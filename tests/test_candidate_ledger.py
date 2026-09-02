"""Guards on the recipe type and the candidate ledger.

The two claims worth pinning are both about *identity*. A recipe key has to
name the pixels and nothing else — not the machine it was computed on, not a
palette clustering that can be recomputed, but yes the autolevel band, which no
other digest in this project carries. And the ledger has to hold one row per
render rather than one per decision, because a pass that seats an earlier pass's
picture writes a second row about the same pixels.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from fractal_wallpapers.curation import candidate_ledger, recipes, release
from fractal_wallpapers.models import renders

BAND = "49d4f43b200904c5967df788308834be163698081d85802df978554261aa63a1"

ORIGINAL_VIEWPORT = {
    "center_re": "-0.4244006261408098",
    "center_im": "-0.574259977676454",
    "width": "0.2841456336596834",
}
REFINED_VIEWPORT = {**ORIGINAL_VIEWPORT, "width": "0.2009309625693763"}


def decision(**over) -> dict:
    """One row in the shape both decision stores hold, with `over` applied on top."""
    row = {
        "schema": 1,
        "key": "gallery9|gate|0000",
        "run": "gallery9",
        "stage": "gate",
        "candidate": "0000",
        "verdict": "kept",
        "picture": "pictures/0000.jpg",
        "location": {
            "key": json.dumps(
                [
                    "mandelbrot",
                    2,
                    [],
                    "-0.4244006261408098",
                    "-0.574259977676454",
                    "0.2841456336596834",
                ]
            ),
            "partition": "mandelbrot",
            "family": {"kind": "mandelbrot", "degree": 2},
            "viewport": dict(ORIGINAL_VIEWPORT),
            "maxiter": 8080,
            "ledger": "artifacts/harvest_run2/walk.jsonl",
        },
        "recipe": {
            "mode": "smooth",
            "mode_kind": "field",
            "curve": "linear",
            "colormap": "magma",
            "mirror": True,
            "render": {"resolution": [640, 360], "supersample": 2, "maxiter": 8080},
        },
        "scores": {"head": "smooth_render", "p_ge2": 0.9, "p_ge3": 0.8, "p_ge4": 0.1},
        "autolevel": {
            "operator": "band_autolevel/v1",
            "switch": "on",
            "acted": False,
            "band": {"path": "levels_band.json", "sha256": BAND},
        },
        "framing": None,
        "rejected": None,
    }
    for name, value in over.items():
        row[name] = value
    return row


# --------------------------------------------------------------------------- #
# The key names the pixels, and only the pixels.
# --------------------------------------------------------------------------- #
def test_the_key_carries_the_band_no_other_digest_carries():
    """The autolevel band is in the key, and it is the reason this is its own digest.

    `band_autolevel/v1` re-renders through a colormap built from the band file,
    so two candidates with one engine spec and two bands are two pictures — and
    `renders.job_name`, the only other digest of a render's identity here, does
    not know the band exists.
    """
    one = recipes.of_decision(decision())
    other = recipes.of_decision(
        decision(
            autolevel={
                "operator": "band_autolevel/v1",
                "switch": "on",
                "acted": False,
                "band": {"path": "levels_band.json", "sha256": "0" * 64},
            }
        )
    )
    assert recipes.key_of(one) != recipes.key_of(other)
    assert renders.job_name(one.row()) == renders.job_name(other.row())


def test_the_key_does_not_carry_a_path():
    """Nothing in the digest names a place on this machine.

    `renders.spec_of` puts an absolute `colormap_dir` in every spec, and the
    render cache digests it — harmless for a file name that means nothing off the
    machine that wrote it, and not harmless for a durable store's key. Both path
    members are dropped, and this is the guard that says the drop is complete.
    """
    material = recipes.of_decision(decision()).pixels()
    text = json.dumps(material)
    assert "colormap_dir" not in text
    assert "output" not in text
    assert set(recipes.PINNED) == {"colormap_dir", "output"}


def test_the_key_does_not_move_with_the_palette_grouping():
    """A re-clustering of the palette groups re-keys nothing. The pixels did not move."""
    one = recipes.of_decision(decision(), {"magma": "m01"})
    other = recipes.of_decision(decision(), {"magma": "m99"})
    assert one.palette_group != other.palette_group
    assert recipes.key_of(one) == recipes.key_of(other)


def test_an_unclassified_member_refuses_rather_than_being_left_out(monkeypatch):
    """A member added to Recipe and left out of both lists cannot be silently unkeyed."""
    monkeypatch.setattr(recipes, "KEYED", tuple(n for n in recipes.KEYED if n != "curve"))
    with pytest.raises(recipes.RecipeError, match="curve"):
        recipes.of_decision(decision()).pixels()


def test_an_unclassified_spec_member_refuses_too(monkeypatch):
    """The same discipline one level down: a new engine axis has to be classified."""
    real = renders.spec_of
    monkeypatch.setattr(
        renders, "spec_of", lambda row, output: {**real(row, output), "perturbation": True}
    )
    with pytest.raises(recipes.RecipeError, match="perturbation"):
        recipes.of_decision(decision()).pixels()


def test_the_stamp_drops_what_the_operator_derived():
    """`acted` is a function of the picture, not an input to it, so it is not in the key."""
    stamp = recipes.stamp_of(decision()["autolevel"])
    assert stamp == {"operator": "band_autolevel/v1", "switch": "on", "band_sha256": BAND}
    acted = recipes.stamp_of({**decision()["autolevel"], "acted": True})
    assert stamp == acted


def test_a_mode_the_operator_does_not_act_on_has_no_band_in_its_key():
    """A direct trap is never levelled, so its recipe carries no band at all."""
    row = decision()
    row["recipe"] = {**row["recipe"], "mode": "direct_trap_ring", "mode_kind": "direct"}
    row["autolevel"] = None
    assert recipes.of_decision(row).autolevel is recipes.NO_AUTOLEVEL


# --------------------------------------------------------------------------- #
# The frame is the one that was rendered.
# --------------------------------------------------------------------------- #
def test_the_recipe_takes_the_framing_that_was_used_not_the_one_adopted():
    """A fallback render of an adopted refinement keys on the frame it actually drew.

    305 of the pool's adopted pictures are exactly this row: the refine leg
    adopted a frame, every attempt on the slot landed under the bar, and the
    fallback leg re-rendered the location at its recorded framing. A key taken
    off `framing.adopted` would hand a solver the refined frame's name for the
    original frame's pixels.
    """
    refined = decision(
        location={**decision()["location"], "viewport": dict(REFINED_VIEWPORT)},
        framing={
            "adopted": True,
            "used": "refined",
            "original": {"viewport": dict(ORIGINAL_VIEWPORT)},
            "refined": {"viewport": dict(REFINED_VIEWPORT)},
        },
    )
    fell_back = decision(
        framing={
            "adopted": True,
            "used": "original",
            "original": {"viewport": dict(ORIGINAL_VIEWPORT)},
            "refined": {"viewport": dict(REFINED_VIEWPORT)},
        },
    )
    assert recipes.of_decision(refined).viewport == REFINED_VIEWPORT
    assert recipes.of_decision(fell_back).viewport == ORIGINAL_VIEWPORT
    assert recipes.key_of(recipes.of_decision(refined)) != recipes.key_of(
        recipes.of_decision(fell_back)
    )


def test_a_row_that_says_original_and_holds_the_refined_frame_is_refused():
    """The two would name one picture and be two, and nothing downstream could tell."""
    lying = decision(
        location={**decision()["location"], "viewport": dict(REFINED_VIEWPORT)},
        framing={
            "adopted": True,
            "used": "original",
            "original": {"viewport": dict(ORIGINAL_VIEWPORT)},
            "refined": {"viewport": dict(REFINED_VIEWPORT)},
        },
    )
    with pytest.raises(recipes.RecipeError, match="ORIGINAL"):
        recipes.of_decision(lying)


def test_the_row_records_both_keys_and_never_reconciles_them():
    """The recorded identity and the frame's identity, both, and which they are."""
    refined = decision(
        location={**decision()["location"], "viewport": dict(REFINED_VIEWPORT)},
        framing={
            "adopted": True,
            "used": "refined",
            "original": {"viewport": dict(ORIGINAL_VIEWPORT)},
            "refined": {"viewport": dict(REFINED_VIEWPORT)},
        },
    )
    recipe = recipes.of_decision(refined)
    stored = candidate_ledger.row(
        recipe=recipe,
        key=recipes.key_of(recipe),
        source={**refined, "_store": candidate_ledger.FROM_GALLERY},
        also_rendered=[],
        colour=None,
        picture=None,
        rejected=None,
    )
    assert stored["location"]["key"] == refined["location"]["key"]
    # The frame's own key is no longer stored beside the recorded one — nothing
    # read it, and it is `_frame_key(recipe)` — so what the row keeps is the one
    # bit of the comparison: they disagree. The claim is the same claim.
    assert stored["location"]["agrees"] is False
    assert stored["location"]["key"] != candidate_ledger._frame_key(recipe)
    assert "frame_key" not in stored["location"]
    assert stored["recipe"]["viewport"] == dict(REFINED_VIEWPORT)


# --------------------------------------------------------------------------- #
# The store.
# --------------------------------------------------------------------------- #
@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """The ledger and its sidecar in a temporary directory, and nothing else touched.

    Five paths and not two. A backfill goes through [`candidate_ledger.merge`],
    which records what it wrote — so an unredirected copy lands on this machine's
    real archive tier and an unredirected manifest lands in the tracked history.
    `tests/test_ledger_tracking.py` owns the rule that makes recording part of the
    write; this is what keeps it inside `tmp_path`.

    The **flatness sidecar** is the fifth, and it is redirected for the same
    reason as the other four rather than a new one: `merge` fills it now, and
    `flatness.sidecar_path()` resolves through `store_root()` — which this fixture
    does not move, because it moves the two row files directly. Without the
    redirect a synthetic three-row merge would upsert into this machine's real
    hundred-thousand-row sidecar.

    The **reduced-signature sidecar** is the sixth and resolves the same way.
    `merge` does not fill that one, only mirrors it, so the cost of forgetting it
    is 68.6 MB copied into `tmp_path` per merge rather than a corrupted store —
    still not something a unit test should do.
    """
    from fractal_wallpapers.curation import flatness, signatures

    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: tmp_path / "rows.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: tmp_path / "scores.jsonl")
    monkeypatch.setattr(candidate_ledger, "backup_path", lambda name: tmp_path / f"copy-{name}")
    monkeypatch.setattr(candidate_ledger, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(candidate_ledger, "_picture_of", lambda source: tmp_path / "nothing.jpg")
    monkeypatch.setattr(flatness, "sidecar_path", lambda: tmp_path / "flatness.jsonl")
    monkeypatch.setattr(signatures, "sidecar_path", lambda: tmp_path / signatures.SIDECAR_NAME)
    return tmp_path


def test_backfill_holds_one_row_per_render_not_one_per_decision(isolated, monkeypatch):
    """A re-stamp is dropped and a duplicate render is merged, both on the picture.

    Three rows, two pictures: a pass seated a run's candidate under its own id
    (`source` names the row it decided over), and a second pass happened to draw
    the same recipe again. The first is one picture wearing two names; the second
    is two renders of one recipe, which is what the ledger exists to stop.
    """
    made = decision()
    seated = decision(
        key="gallery9|release|0000",
        run="gallery9",
        candidate="0000",
        source={"run": "run9", "candidate": "0007", "key": "run9|release|0007"},
    )
    made["key"], made["run"], made["candidate"] = "run9|release|0007", "run9", "0007"
    twin = decision(key="gallery8|gate|0031", run="gallery8", candidate="0031")

    monkeypatch.setattr(
        candidate_ledger,
        "sources",
        lambda: [
            {**made, "_store": candidate_ledger.FROM_RELEASE},
            {**seated, "_store": candidate_ledger.FROM_RELEASE},
            {**twin, "_store": candidate_ledger.FROM_GALLERY},
        ],
    )
    report = candidate_ledger.backfill(log=lambda *_: None)
    assert report["rows_read"] == 3
    assert report["restamps"] == 1
    assert report["recipes"] == 1
    assert report["duplicate_renders"] == 1

    (stored,) = candidate_ledger.read()
    assert stored["provenance"]["run"] == "gallery8"
    assert [other["run"] for other in stored["provenance"]["also_rendered"]] == ["run9"]


def test_a_second_backfill_over_an_unchanged_pool_writes_the_same_bytes(isolated, monkeypatch):
    """A store that churned on a re-read would make every manifest a moving target."""
    monkeypatch.setattr(
        candidate_ledger,
        "sources",
        lambda: [{**decision(), "_store": candidate_ledger.FROM_GALLERY}],
    )
    candidate_ledger.backfill(log=lambda *_: None)
    once = (isolated / "rows.jsonl").read_bytes()
    candidate_ledger.backfill(log=lambda *_: None)
    assert (isolated / "rows.jsonl").read_bytes() == once


def test_the_sidecar_folds_two_spellings_of_one_artifact_onto_one(monkeypatch):
    """A run abbreviates a head stamp to sixteen hex and a floor carries all sixty-four."""
    from fractal_wallpapers.curation import rescore

    monkeypatch.setattr(rescore, "artifact_of", lambda row: row["_stamp"])
    folded = candidate_ledger.canonical_artifacts(
        [{"_stamp": "e62e8dbab7f47ffe"}, {"_stamp": "e62e8dbab7f47ffe" + "a" * 48}]
    )
    assert len(set(folded.values())) == 1
    assert folded["e62e8dbab7f47ffe"] == "e62e8dbab7f47ffe" + "a" * 48


def test_the_score_sidecar_is_keyed_on_the_triple_a_number_is_comparable_within():
    """Recipe, judge artifact, regime. A judge adoption invalidates scores and nothing else."""
    stamped = candidate_ledger.score_row(
        key="abcd1234abcd1234",
        artifact="e" * 64,
        regime=recipes.CANDIDATE_REGIME.spelled,
        head="smooth_render",
        read={"p_ge3": 0.8, "p_ge4": 0.1},
        source={"run": "run9", "candidate": "0007"},
    )
    assert stamped["key"] == f"abcd1234abcd1234|{'e' * 64}|640x360ss2"
    assert stamped["p_ge3"] == 0.8


def test_the_candidate_regime_is_read_off_the_row_not_assumed():
    """Everything on record stands at one regime, and a row that does not is flagged."""
    assert release.Regime((640, 360), 2) == recipes.CANDIDATE_REGIME
    assert recipes.is_candidate_regime(recipes.of_decision(decision()))
    bigger = decision()
    bigger["recipe"] = {
        **bigger["recipe"],
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 8080},
    }
    assert not recipes.is_candidate_regime(recipes.of_decision(bigger))


# --------------------------------------------------------------------------- #
# The tracked pool.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_every_candidate_on_record_becomes_a_recipe():
    """A row the ledger cannot name is a picture nothing can find again."""
    from fractal_wallpapers.palettes import groups as groups_module

    table = groups_module.member_groups()
    refused = []
    for source in candidate_ledger.sources():
        try:
            recipe = recipes.of_decision(source, table)
        except recipes.RecipeError as refusal:
            refused.append((source["key"], str(refusal)))
            continue
        assert recipes.is_candidate_regime(recipe), source["key"]
    assert refused == []


@pytest.mark.slow
def test_a_key_that_is_not_its_frame_is_always_a_refined_frame_row():
    """The disagreement is the refine leg's pinned identity and never anything else.

    A gallery pass keeps a location's recorded key while rendering somewhere else
    inside it, which is what stops one place taking two seats. Any row where the
    two disagree for another reason would be a row the ledger's location axis
    counts in the wrong place.
    """
    from fractal_wallpapers.palettes import groups as groups_module

    table = groups_module.member_groups()
    for source in candidate_ledger.sources():
        recipe = recipes.of_decision(source, table)
        stored = candidate_ledger.row(
            recipe=recipe,
            key=recipes.key_of(recipe),
            source=source,
            also_rendered=[],
            colour=None,
            picture=None,
            rejected=None,
        )
        if stored["location"]["agrees"]:
            continue
        block = source.get("framing") or {}
        assert block.get("adopted") and block.get("used") == "refined", source["key"]


@pytest.mark.slow
def test_the_recipe_dataclass_says_what_a_ledger_row_stores():
    """Every member of the type is on the record, keyed or carried, and nothing else is."""
    members = {field.name for field in dataclasses.fields(recipes.Recipe)}
    assert members == set(recipes.KEYED) | set(recipes.CARRIED)
    stored = recipes.of_decision(decision()).record()
    assert members <= set(stored)


# --------------------------------------------------------------------------- #
# The stored colour, and the lens served off it.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_the_stored_colour_block_is_what_the_picture_still_reads_as(tracked_ledger):
    """The lens serves the stored block instead of decoding, so the two paths
    have to be one answer. A sample rather than every row because a decode is
    16 ms a row: this is the guard that catches a drift, not a re-census. The
    rows are the session's one reading; see `conftest.tracked_ledger`."""
    import random
    from pathlib import Path

    from fractal_wallpapers.palettes import dominance
    from fractal_wallpapers.paths import rehome

    rows = [
        row
        for row in tracked_ledger.rows
        if row.get("picture") and row.get("colour") and not row.get("rejected")
    ]
    assert rows, "the ledger has rows with a picture and a colour"
    sample = random.Random(20260827).sample(rows, min(80, len(rows)))
    checked, wrong = 0, []
    for row in sample:
        picture = Path(rehome(row["picture"]))
        if not picture.is_file():
            continue
        checked += 1
        live = candidate_ledger.colour_block(dominance.of_picture(picture))
        if live != row["colour"]:
            wrong.append(row["key"])
    assert checked, "the sample found no picture on this machine"
    assert wrong == [], f"{len(wrong)} of {checked} stored readings disagree with the pixels"


def _picture_row(key, name):
    return {
        "key": key,
        "picture": name,
        "recipe": {"mode": "smooth"},
        "provenance": {"run": "run1"},
    }


def test_present_pictures_answers_the_disk_and_not_the_row(tmp_path, monkeypatch):
    """PLANTED: two rows name a picture and only one of them has one.

    `curate retention` drops pictures and never rows, so this is the store's
    normal state over about a quarter of it — and a reader that trusted the name
    is what let `solve.pool` admit 30,040 rows nothing could open.
    """
    from fractal_wallpapers import paths
    from fractal_wallpapers.curation import candidate_ledger

    root = tmp_path / "artifacts"
    (root / "run1").mkdir(parents=True)
    (root / "run1" / "here.jpg").touch()
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))

    rows = [
        _picture_row("a", "artifacts/run1/here.jpg"),
        _picture_row("b", "artifacts/run1/swept.jpg"),
        _picture_row("c", None),
    ]
    assert candidate_ledger.present_pictures(rows) == {"a"}


def test_the_picture_census_counts_the_absent_by_mode_and_by_run(tmp_path, monkeypatch):
    from fractal_wallpapers import paths
    from fractal_wallpapers.curation import candidate_ledger

    root = tmp_path / "artifacts"
    (root / "run1").mkdir(parents=True)
    (root / "run1" / "here.jpg").touch()
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))

    rows = [
        _picture_row("a", "artifacts/run1/here.jpg"),
        _picture_row("b", "artifacts/run1/swept.jpg"),
    ]
    rows[1]["recipe"]["mode"] = "stripe"
    rows[1]["provenance"]["run"] = "run2"

    census = candidate_ledger.picture_census(rows)
    assert census["rows"] == 2
    assert census["with_a_picture_on_disk"] == 1
    assert census["naming_a_picture_that_is_absent"] == 1
    assert census["by_mode"]["stripe"]["absent"] == 1
    assert census["by_mode"]["smooth"]["absent"] == 0
    assert census["by_run"]["run2"]["absent"] == 1


# --------------------------------------------------------------------------- #
# The compact row, and the two invariants it is cut against.
# --------------------------------------------------------------------------- #
#: Every member a ledger row may carry, at every level. A field that came back
#: would be a field no reader asked for — the whole row was derived from the
#: reader sites — so this is spelled out rather than counted, and adding to it
#: is a decision.
ROW_MEMBERS = {
    "": {
        "schema",
        "key",
        "partition",
        "location",
        "recipe",
        "at_candidate_regime",
        # A bare boolean and the second derived member the row stores, because
        # re-deriving it costs a render — see [`coloring.texture_flat`]. Five
        # readers take it: the seating pool, the census, the two label-store
        # routers and the mode floors that follow the pool.
        "texture_flat",
        "colour",
        "provenance",
        "picture",
        "rejected",
        "hunt",
    },
    "location": {"key", "agrees"},
    "colour": {"cells", "families"},
    "provenance": {"run", "candidate", "also_rendered", "also_recorded"},
    "hunt": {"seconds", "k"},
}


def test_the_row_carries_only_the_members_the_readers_consume():
    """The row is 3,027 bytes of history cut to about 1,300 of readers.

    Spelled out and not counted, because the failure this catches is a field
    quietly rejoining: the set was derived by tracing every reader site, and a
    member nobody derived is a member nobody reads.
    """
    source = decision()
    recipe = recipes.of_decision(source)
    stored = candidate_ledger.row(
        recipe=recipe,
        key=recipes.key_of(recipe),
        source={**source, "_store": candidate_ledger.FROM_GALLERY},
        colour={"cells": ["dark_vivid_green"], "families": ["green"], "neutral": 0.1},
        picture="artifacts/x.jpg",
    )
    stored["hunt"] = candidate_ledger.hunt_block({"seconds": 1.0, "k": 3, "leg": "flat"})
    assert set(stored) == ROW_MEMBERS[""]
    for block in ("location", "colour", "provenance", "hunt"):
        assert set(stored[block]) == ROW_MEMBERS[block], block


def test_the_colour_block_keeps_the_verdict_and_not_the_shares():
    """`cells` and `families` are the reading; the share vectors were the same
    reading in a form nothing could act on, at 678 bytes a row."""
    wide = {
        "cells": ["dark_vivid_green"],
        "families": ["green"],
        "cell_shares": {"dark_vivid_green": 0.42},
        "family_shares": {"green": 0.42},
        "neutral": 0.21,
    }
    assert candidate_ledger.colour_kept(wide) == {
        "cells": ["dark_vivid_green"],
        "families": ["green"],
    }
    assert candidate_ledger.colour_kept(None) is None
    assert candidate_ledger.colour_kept({}) is None


def test_the_hunt_block_keeps_the_seconds_and_the_draw_and_nothing_else():
    """Two fields of nine. `seconds` prices a leg and `k` corrects the winner's
    curse; the other seven were the recipe's or the run's, spelled again."""
    block = candidate_ledger.hunt_block(
        {
            "name": "a_leg",
            "seconds": 0.09,
            "leg": "conditioned",
            "mode": "stripe",
            "colormap": "winter",
            "band": "band00",
            "k": 10,
            "rank": 14,
            "drawn_for": "light_vivid_teal",
        }
    )
    assert block == {"seconds": 0.09, "k": 10}
    assert candidate_ledger.k_of({"hunt": block}) == 10


def test_a_recipe_read_back_off_a_stored_row_recomputes_the_row_s_own_key():
    """**Invariant one.** The store's name for a picture is derivable from the
    row rather than trusted off it, which is what lets the row drop the rest."""
    source = decision()
    recipe = recipes.of_decision(source)
    key = recipes.key_of(recipe)
    stored = candidate_ledger.row(
        recipe=recipe, key=key, source={**source, "_store": candidate_ledger.FROM_GALLERY}
    )
    assert recipes.key_of(recipes.of_record(stored["recipe"])) == key


def test_a_recipe_read_back_off_a_stored_row_is_an_engine_spec():
    """**Invariant two.** The picture is re-renderable from the row alone."""
    source = decision()
    recipe = recipes.of_decision(source)
    stored = candidate_ledger.row(
        recipe=recipe, key=recipes.key_of(recipe), source={**source, "_store": "gallery"}
    )
    spec = recipes.of_record(stored["recipe"]).row()
    assert spec["family"] == stored["recipe"]["family"]
    assert spec["viewport"] == stored["recipe"]["viewport"]
    assert spec["render"]["resolution"] and spec["render"]["maxiter"]


def test_a_stored_recipe_missing_a_member_refuses_rather_than_defaulting_one():
    """A recipe read back with a guessed knob digests to a key that names a
    different picture, and a silently wrong identity is worse than none."""
    source = decision()
    block = recipes.of_decision(source).record()
    with pytest.raises(recipes.RecipeError, match="curve"):
        recipes.of_record({**block, "curve": None})


def test_there_is_one_ledger_and_the_three_files_sit_together_in_it():
    """The store held two ledgers side by side while the wide one was being
    replaced, addressed by a `which` on five functions and a `LIVE` constant. The
    wide one was deleted on 2026-08-29; a constant naming a file that is not there
    is the kind of name this repository renames on the way in."""
    from fractal_wallpapers.curation import flatness

    for gone in ("WIDE", "RETAINED", "LIVE", "ledger_root"):
        assert not hasattr(candidate_ledger, gone), gone
    root = candidate_ledger.store_root()
    assert candidate_ledger.rows_path().parent == root
    assert candidate_ledger.scores_path().parent == root
    assert flatness.sidecar_path().parent == root
    assert flatness.durable().manifest.parent == candidate_ledger.manifest_dir()


# --------------------------------------------------------------------------- #
# The rule the merge holds the store to.
# --------------------------------------------------------------------------- #
def pruned_rows(rows, values, keep, protected=()):
    """What `prune` keeps, as its own two-step composition over given rows.

    `prune` itself reads the rank key, the release index, the label stores and the
    fitted population, none of which a fast test has. What it *does* with them is
    this: a ranking, then a union with the protections. So that composition is
    what is pinned here, and `test_the_prune_is_the_only_thing_that_deletes`
    below holds that `prune` has no second rule in it.
    """
    from fractal_wallpapers.curation import retention

    verdicts = retention.decide(rows, values, keep=keep)
    return {
        str(row["key"])
        for row in rows
        if retention.kept(verdicts[str(row["key"])]) or str(row["key"]) in set(protected)
    }


def paired(place, mode, count, start=0):
    return [
        {
            "key": f"{place}-{mode}-{at}",
            "location": {"key": place},
            "recipe": {"mode": mode},
            "picture": f"artifacts/curation/hunt/h/pictures/{place}-{mode}-{at}.jpg",
        }
        for at in range(start, start + count)
    ]


def test_rows_per_location_mode_cannot_exceed_the_constant_unless_a_protection_names_them():
    """**The growth law.** Without this the file is back where it started in a
    few weeks: a rule nothing enforces is not a rule.

    The bound is `RETAIN_PER_PAIR` *plus whatever the five protections carry*, and
    it is stated that way because the protections genuinely do exceed it — over
    the store on 2026-08-29, 395 of 48,154 pairs held more than three rows and the
    425 rows beyond the constant are exactly the 425 the protections saved. A
    guard that asserted a flat ceiling would be asserting the protections do not
    work."""
    keep = candidate_ledger.RETAIN_PER_PAIR
    rows = paired("p", "smooth", 20) + paired("p", "stripe", 20) + paired("q", "smooth", 20)
    values = {row["key"]: at for at, row in enumerate(rows)}
    protected = {"p-smooth-0", "p-smooth-1"}

    kept = pruned_rows(rows, values, keep, protected)
    per_pair: dict = {}
    for row in rows:
        if str(row["key"]) in kept:
            pair = (row["location"]["key"], row["recipe"]["mode"])
            per_pair[pair] = per_pair.get(pair, 0) + 1
    assert per_pair[("p", "stripe")] == keep
    assert per_pair[("q", "smooth")] == keep
    assert per_pair[("p", "smooth")] == keep + len(protected)
    unprotected = {pair: count for pair, count in per_pair.items() if pair != ("p", "smooth")}
    assert max(unprotected.values()) <= keep


def test_the_rows_and_the_pictures_agree_in_both_directions():
    """One rule means the two sets are the same set. A dropped row's picture is on
    the delete list, and a kept row's picture is not — the failure the two-K era
    had was the second half, a row inside the rank whose picture another ranking
    had already taken."""
    keep = candidate_ledger.RETAIN_PER_PAIR
    rows = paired("p", "smooth", 10)
    values = {row["key"]: at for at, row in enumerate(rows)}
    kept = pruned_rows(rows, values, keep)

    doomed = {row["picture"] for row in rows if str(row["key"]) not in kept}
    standing = {row["picture"] for row in rows if str(row["key"]) in kept}
    assert doomed & standing == set(), "a picture cannot be kept and deleted at once"
    assert doomed | standing == {row["picture"] for row in rows}, "every picture is decided"
    assert len(standing) == keep


def test_the_prune_is_the_only_thing_that_deletes_and_it_runs_from_the_merge():
    """The wiring itself, because everything above this is a one-time cleanup
    without it. `merge` is THE door every leg comes through, so it is the only
    place the rule has to stand."""
    import inspect

    source = inspect.getsource(candidate_ledger.merge)
    assert "prune(" in source, "a merge that does not prune lets the store grow again"
    assert "repeat_draws" in source, "the price of the rule is reported per leg"

    body = inspect.getsource(candidate_ledger.prune)
    assert "delete_pictures(" in body, "the rows and their pictures go in one call"
    assert body.index("delete_pictures(") < body.index("_prune_file("), (
        "pictures first: a crash after the record transaction leaves pictures nothing "
        "names, which no reader can find and no run can free"
    )


def a_pair(pictures: Path, key: str) -> None:
    """One candidate on disk as `colorize.render` leaves it: the JPEG and, where
    the autolevel operator acted, the overriding colormap in `<stem>.leveled/`."""
    pictures.mkdir(parents=True, exist_ok=True)
    (pictures / f"{key}.jpg").write_bytes(b"0" * 32)
    (pictures / f"{key}.leveled").mkdir(exist_ok=True)
    (pictures / f"{key}.leveled" / "viridis.json").write_text('{"stops": []}', encoding="utf-8")


def test_a_dropped_picture_takes_its_levelled_colormap_with_it(tmp_path, monkeypatch):
    """The rule is that a picture goes with its row, and the levelled colormap is
    part of what that render cost — ~76 KiB beside a ~157 KiB JPEG, on every
    acted render. Unlinking the one and leaving the other is how 206,147 of them
    reached 14.9 GiB, more than the whole candidate pool, entirely outside the
    retention rule and invisible to the function that was supposed to be the only
    thing deleting a candidate's artifacts."""
    from fractal_wallpapers import paths

    root = tmp_path / "artifacts"
    pictures = root / "curation" / "depth" / "a_leg" / "pictures"
    a_pair(pictures, "dropped")
    a_pair(pictures, "kept")
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))

    record = candidate_ledger.delete_pictures(
        ["artifacts/curation/depth/a_leg/pictures/dropped.jpg"], log=lambda *_: None
    )

    assert record["deleted"] == 1 and record["bytes"] == 32
    assert record["colormaps"] == 1 and record["colormap_bytes"] == 13
    assert not (pictures / "dropped.jpg").exists()
    assert not (pictures / "dropped.leveled").exists()
    # The row nobody dropped keeps both halves of what its render made.
    assert (pictures / "kept.jpg").is_file()
    assert (pictures / "kept.leveled" / "viridis.json").is_file()


def test_the_colormap_goes_even_where_the_picture_was_already_swept(tmp_path, monkeypatch):
    """The row is being dropped either way, and a colormap outliving a picture
    somebody already deleted is precisely the pile. Counted as an absent picture
    and a deleted colormap, which is what happened."""
    from fractal_wallpapers import paths

    root = tmp_path / "artifacts"
    pictures = root / "curation" / "depth" / "a_leg" / "pictures"
    a_pair(pictures, "half_gone")
    (pictures / "half_gone.jpg").unlink()
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))

    record = candidate_ledger.delete_pictures(
        ["artifacts/curation/depth/a_leg/pictures/half_gone.jpg"], log=lambda *_: None
    )

    assert record["absent"] == 1 and record["deleted"] == 0
    assert record["colormaps"] == 1
    assert not (pictures / "half_gone.leveled").exists()


def test_a_name_this_project_did_not_write_reaches_neither_half(tmp_path, monkeypatch):
    """`rehome` answers `None` for a name with no artifacts component, and that
    has always kept a fixture's `a.jpg` out of reach of this. The colormap sweep
    is inside the same refusal rather than beside it — a second path built before
    the check is exactly how this function would grow a way out of the tree."""
    from fractal_wallpapers import paths

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir()
    a_pair(tmp_path / "elsewhere", "a")

    record = candidate_ledger.delete_pictures(["elsewhere/a.jpg"], log=lambda *_: None)

    assert record == {
        "asked": 1,
        "deleted": 0,
        "bytes": 0,
        "absent": 1,
        "unreadable": 0,
        "colormaps": 0,
        "colormap_bytes": 0,
        "gib": 0.0,
        "colormap_gib": 0.0,
    }
    assert (tmp_path / "elsewhere" / "a.jpg").is_file()
    assert (tmp_path / "elsewhere" / "a.leveled" / "viridis.json").is_file()


def test_a_prune_reads_the_store_through_the_accessors_and_never_off_the_root(
    isolated, monkeypatch
):
    """**The guard this cost 266 pictures to learn.** A test redirects this store
    by patching `rows_path`, `scores_path` and `flatness.sidecar_path` by name.
    `prune` rebuilt all three off `store_root()`, which the fixture does not
    move, so a three-row merge in a temporary directory read the real hundred-
    thousand-row ledger, ranked it against its own empty sidecars, and rewrote
    it — deleting the pictures of the rows the broken ranking dropped.

    Two failures in one shape, and this catches either: reading past the
    redirect, and reading a path that does not exist. `_stream_of` answers a
    missing file with nothing, so a prune that built the wrong path decided over
    an empty store and wrote three empty files rather than raising."""
    rows = []
    for at in range(3):
        source = decision(key=f"gallery9|gate|{at:04d}", candidate=f"{at:04d}")
        recipe = recipes.of_decision(source)
        rows.append(
            candidate_ledger.row(
                recipe=recipe,
                key=f"k{at}",
                source={**source, "_store": candidate_ledger.FROM_GALLERY},
                picture=None,
            )
        )
    candidate_ledger.write(rows)
    record = candidate_ledger.prune(log=lambda *_: None)

    assert record["rows_read"] == 3, "the prune read past the redirect, or read nothing at all"
    assert record["rows_kept"] == 3
    assert len(candidate_ledger.read()) == 3
    assert candidate_ledger.rows_path().parent == isolated


# --------------------------------------------------------------------------- #
# Putting a picture back.
# --------------------------------------------------------------------------- #
def test_the_re_render_selects_on_the_retention_rule_and_nothing_else(isolated, monkeypatch):
    """A row is in the work list because it survived the prune and its JPEG is
    gone. No bar, no mode roster, no clearing test — a second implicit picture
    policy is exactly what collapsing `KEEP_PER_PAIR` into the row rule deleted,
    and it would grow back here first if anything filtered this list."""
    here = isolated / "pictures"
    here.mkdir()
    (here / "kept.jpg").write_bytes(b"x")
    rows = []
    for key, picture in (("kept", here / "kept.jpg"), ("gone", here / "gone.jpg")):
        source = decision()
        rows.append(
            candidate_ledger.row(
                recipe=recipes.of_decision(source), key=key, source=source, picture=str(picture)
            )
        )
    candidate_ledger.write(rows)

    monkeypatch.setattr(candidate_ledger, "present_pictures", lambda stored: {"kept"})
    wanted = candidate_ledger.missing_pictures()
    assert [str(row["key"]) for row in wanted] == ["gone"]


def test_a_row_naming_no_picture_is_not_something_to_render():
    """`None` is not a missing file. A row that never named a picture has nothing
    to put back, and rendering one would invent a name the store never chose."""
    import inspect

    source = inspect.getsource(candidate_ledger.missing_pictures)
    assert 'row.get("picture")' in source


def test_the_re_render_refuses_a_row_it_cannot_reproduce_exactly():
    """**The guard the whole leg rests on.** The recipe the render path derives —
    palette knobs off the cyclic set, the autolevel stamp off the shipped band —
    is digested, and the row is rendered only if that digest is the row's own key.

    A row where the two disagree would get DIFFERENT pixels under its own name,
    which is worse than having no picture: every score and every flatness reading
    in the sidecars was read on the pixels that used to be there."""
    import inspect

    source = inspect.getsource(candidate_ledger.re_render)
    assert "recipes.key_of(" in source
    assert 'if again != str(row["key"]):' in source
    assert source.index("refused.append") < source.index("jobs.append"), (
        "the key check has to come before the job is queued, not after it is rendered"
    )


def test_the_re_render_writes_pictures_and_nothing_else(isolated):
    """It repairs the disk, never the store. A leg that also touched the rows,
    a sidecar or a manifest would be a repair nobody asked for running inside one
    that was — and the sidecars' numbers were read on the pixels it is restoring,
    so they are already right."""
    import inspect

    source = inspect.getsource(candidate_ledger.re_render)
    for forbidden in ("write(", "write_scores(", "durability.save", "upsert", "prune("):
        assert forbidden not in source, forbidden


def test_nothing_but_the_ledger_deletes_a_candidate_picture():
    """One delete in this project, in one module, reachable from one function.

    Asked of **both** verbs, because a candidate now costs two things on disk. A
    picture is unlinked and a levelled colormap is a directory, so a sweeper that
    grew `rmtree` somewhere this only asked about `unlink` would be a second way
    to destroy a candidate that this guard would have called clean."""
    import inspect

    from fractal_wallpapers.curation import retention

    def owners(verb: str) -> list[str]:
        return sorted(
            name
            for name, held in vars(candidate_ledger).items()
            if inspect.isfunction(held)
            and held.__module__ == candidate_ledger.__name__
            and verb in inspect.getsource(held)
        )

    assert "unlink(" not in inspect.getsource(retention)
    assert "rmtree(" not in inspect.getsource(retention)
    # `rescore` is the third only because it drops the chunk file it wrote for
    # itself, for `re_render`'s reason below: a leg's own working file is not a
    # candidate, and neither of them can reach a picture.
    assert owners("unlink(") == ["delete_pictures", "prune", "rescore"]
    # `re_render` is the second only because it drops the shared field directory
    # it dumped for itself, which is its own working file and not a candidate's.
    assert owners("rmtree(") == ["_delete_colormap", "re_render"]
    # One definition and one call site, and the call site is past every outcome
    # the JPEG can have — a second one inside a branch is how the sweep comes to
    # be skipped for exactly the rows whose picture was already the odd case.
    assert inspect.getsource(candidate_ledger).count("_delete_colormap(") == 2
    assert "_delete_colormap(" in inspect.getsource(candidate_ledger.delete_pictures)


# --------------------------------------------------------------------------- #
# The orphan sweep: the backstop under the prune, and its isolation.
# --------------------------------------------------------------------------- #
@pytest.fixture
def swept(tmp_path, monkeypatch):
    """A whole artifacts tree in `tmp_path`, and the real one out of reach.

    One redirect isolates the sweep entirely, which is the property worth having:
    `picture_dirs` resolves through `under("curation", ...)` and `stream` resolves
    through `store_root()`, so both follow the hot root and neither can be moved
    independently of the other. A fixture that redirected the store by name — the
    way `isolated` does, for `prune`'s reasons — would leave the sweep's
    enumeration pointed at this machine's real hundred-and-eighty-thousand
    pictures.
    """
    from fractal_wallpapers import paths

    root = tmp_path / "artifacts"
    root.mkdir()
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    return root


def a_leg(root: Path, subtree: str, leg: str, keys, record: str | None = None) -> Path:
    """One leg on disk as a run leaves it: pictures, levelled colormaps, records."""
    pictures = root / "curation" / subtree / leg / "pictures"
    pictures.mkdir(parents=True, exist_ok=True)
    for key in keys:
        a_pair(pictures, key)
    if record is not None:
        (pictures.parent / "sequence.jsonl").write_text(record, encoding="utf-8", newline="\n")
    return pictures


def a_ledger_row(picture: str, merged: bool = True) -> dict:
    """The two fields the sweep reads off a row: where the picture is, and whether
    the row got here through `merge`. `merged=False` is a backfilled row."""
    row = {"schema": candidate_ledger.SCHEMA, "key": picture, "picture": picture}
    return {**row, "hunt": candidate_ledger.hunt_block(None)} if merged else row


def test_a_merged_leg_is_decided_by_the_ledger_alone_and_its_records_do_not_save_a_picture(
    swept,
):
    """Once a leg has merged, a picture with no row is one the retention rule has
    already decided about. `sequence.jsonl` still naming it is a measurement record
    outliving a decision, and it does not buy the file a reprieve."""
    pictures = a_leg(
        swept,
        "depth",
        "a_leg",
        ("in_the_ledger", "in_the_record", "named_by_nothing"),
        record='{"picture": "pictures/in_the_record.jpg"}\n',
    )
    candidate_ledger.write(
        [a_ledger_row("artifacts/curation/depth/a_leg/pictures/in_the_ledger.jpg")]
    )

    record = candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert record["unmerged"] == [], "one row under this leg is the merge stamp"
    assert record["pictures_on_disk"] == 3
    assert record["carrying_no_ledger_row"] == {"depth": 2}
    assert record["named_by_nothing"] == 2
    assert record["pictures"]["deleted"] == 2
    assert (pictures / "in_the_ledger.jpg").is_file()
    assert not (pictures / "in_the_record.jpg").exists()
    assert not (pictures / "named_by_nothing.jpg").exists()
    # The levelled colormap goes with the picture, the same rule the prune keeps.
    assert not (pictures / "named_by_nothing.leveled").exists()
    assert not (pictures / "in_the_record.leveled").exists()


def test_an_unmerged_leg_is_skipped_and_listed_and_nothing_in_it_is_touched(swept):
    """The case the whole command exists for is the one it must not act on alone.
    A leg the ledger has never heard of is a killed leg's real work, and the answer
    is a person's — `merge` it, which costs nothing on a partial, or delete it."""
    killed = a_leg(swept, "depth", "killed_leg", ("a", "b"))
    merged = a_leg(swept, "depth", "merged_leg", ("kept", "loose"))
    candidate_ledger.write([a_ledger_row("artifacts/curation/depth/merged_leg/pictures/kept.jpg")])

    record = candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert [held["leg"] for held in record["unmerged"]] == ["artifacts/curation/depth/killed_leg"]
    assert record["unmerged"][0]["pictures"] == 2
    assert record["unmerged"][0]["ledger_named"] == 0, "the ledger never heard of it"
    assert record["unmerged"][0]["why"] == "unmerged — re-merge or delete"
    assert record["unmerged_legs"] == 1
    assert record["skipped_unmerged"] == 2
    assert record["by_subtree"]["depth"]["unmerged_legs"] == 1
    assert (killed / "a.jpg").is_file() and (killed / "b.jpg").is_file()
    # And the merged leg beside it is swept as usual, so the skip is per leg.
    assert record["named_by_nothing"] == 1
    assert (merged / "kept.jpg").is_file()
    assert not (merged / "loose.jpg").exists()


def test_the_dry_run_is_the_default_and_it_touches_nothing(swept):
    """The opposite way round from `prune`, deliberately: this decides about files
    nothing ever wrote down, so the safe answer has to be the one you get by
    typing less."""
    pictures = a_leg(swept, "depth", "a_leg", ("in_the_ledger", "gone_if_applied"))
    candidate_ledger.write(
        [a_ledger_row("artifacts/curation/depth/a_leg/pictures/in_the_ledger.jpg")]
    )

    record = candidate_ledger.orphans(log=lambda *_: None)

    assert record["applied"] is False
    assert record["pictures"] == {"would_delete": 1}
    assert (pictures / "gone_if_applied.jpg").is_file()


def test_a_backfilled_leg_is_not_a_merged_leg_however_many_rows_name_it(swept):
    """The `runs` era is in this ledger by `backfill`, which reads the two DECISION
    stores — so the ledger holds what those runs decided about and never what they
    rendered. 11,875 rows against 15,578 pictures on 2026-09-02, and the 3,703
    difference is attempts nothing ever decided to drop. Row presence alone would
    have called that a stamp and swept them."""
    pictures = a_leg(swept, "runs", "gallery4", ("decided", "an_attempt"))
    candidate_ledger.write(
        [a_ledger_row("artifacts/curation/runs/gallery4/pictures/decided.jpg", merged=False)]
    )

    record = candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert record["named_by_nothing"] == 0, "a backfilled leg carries no merge stamp"
    assert record["unmerged"][0]["leg"] == "artifacts/curation/runs/gallery4"
    # And the count that tells a backfilled leg from a killed one, at a glance.
    assert record["unmerged"][0]["ledger_named"] == 1
    assert (pictures / "an_attempt.jpg").is_file()


def test_an_unmerged_leg_is_swept_only_when_the_caller_names_it(swept):
    """The listing is the safety and naming a leg is the whole of how it is spent.
    Named, an unmerged leg is swept under the SAME rule as a merged one — what the
    ledger names is kept, the rest goes — which is why the two kinds need no
    separate handling: a killed leg has no rows and loses everything, a backfilled
    `runs` leg keeps every picture its decision stores named."""
    killed = a_leg(swept, "depth", "p1_near", ("a", "b"))
    backfilled = a_leg(swept, "runs", "gallery4", ("decided", "an_attempt"))
    candidate_ledger.write(
        [a_ledger_row("artifacts/curation/runs/gallery4/pictures/decided.jpg", merged=False)]
    )

    # Unnamed, both are listed and neither is touched.
    listed = candidate_ledger.orphans(apply=True, log=lambda *_: None)
    assert listed["unmerged_legs"] == 2
    assert listed["swept_unmerged"] == []
    assert (killed / "a.jpg").is_file() and (backfilled / "an_attempt.jpg").is_file()

    # Named — by its tail here, which is what a person reading the listing types.
    record = candidate_ledger.orphans(
        apply=True, unmerged=("p1_near", "gallery4"), log=lambda *_: None
    )
    assert record["unmerged_legs"] == 0, "both were named, so neither is merely listed"
    assert record["swept_unmerged_legs"] == 2
    assert record["swept_unmerged_pictures"] == 3
    assert not (killed / "a.jpg").exists() and not (killed / "b.jpg").exists()
    assert not (backfilled / "an_attempt.jpg").exists()
    assert (backfilled / "decided.jpg").is_file(), "the ledger names it, so it stays"


def test_naming_one_unmerged_leg_leaves_the_others_listed(swept):
    """Per leg, because the three rulings this was built for were three different
    decisions about three different sets of legs."""
    kept = a_leg(swept, "depth", "lav2", ("a",))
    a_leg(swept, "depth", "teal_pilot", ("b",))
    candidate_ledger.write([])

    record = candidate_ledger.orphans(
        apply=True, unmerged=("artifacts/curation/depth/teal_pilot",), log=lambda *_: None
    )

    assert [held["leg"] for held in record["unmerged"]] == ["artifacts/curation/depth/lav2"]
    assert [held["leg"] for held in record["swept_unmerged"]] == [
        "artifacts/curation/depth/teal_pilot"
    ]
    assert (kept / "a.jpg").is_file()


def test_all_unmerged_is_a_word_and_not_a_bare_true(swept):
    """One type for the parameter: a caller either names legs or names all of them,
    and a string that is neither is refused rather than read as an empty list."""
    a_leg(swept, "depth", "a_leg", ("a",))
    candidate_ledger.write([])

    record = candidate_ledger.orphans(
        apply=False, unmerged=candidate_ledger.ALL_UNMERGED, log=lambda *_: None
    )
    assert record["swept_unmerged_legs"] == 1

    with pytest.raises(candidate_ledger.LedgerError):
        candidate_ledger.orphans(unmerged="a_leg", log=lambda *_: None)


def test_the_sweep_cannot_reach_a_leg_s_fields_however_large_they_get(swept):
    """`fields/` is 6.2 GiB of `.f32` that no record names, and it is NOT this
    command's to delete — the enumeration is a fixed shape at a fixed depth, so a
    directory beside `pictures/` is not reachable whatever it holds."""
    a_leg(swept, "depth", "a_leg", ())
    fields = swept / "curation" / "depth" / "a_leg" / "fields"
    fields.mkdir(parents=True)
    (fields / "0000.f32").write_bytes(b"0" * 64)
    # A JPEG in there too, so this is about the shape and not about the suffix.
    (fields / "stray.jpg").write_bytes(b"0" * 64)
    candidate_ledger.write([])

    candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert (fields / "0000.f32").is_file()
    assert (fields / "stray.jpg").is_file()
    assert [where.name for where in candidate_ledger.picture_dirs()] == ["pictures"]


def test_the_sweep_looks_at_the_five_pool_subtrees_and_no_others(swept):
    """The ledger's pictures live in exactly five subtrees. A sixth holding
    pictures is somebody else's, and this must not discover it."""
    a_leg(swept, "depth", "a_leg", ("a",))
    a_leg(swept, "manufacture", "a_leg", ("b",))
    a_leg(swept, "neutral", "a_leg", ("c",))
    candidate_ledger.write([])

    record = candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert record["pictures_on_disk"] == 1, "it swept outside the five pool subtrees"
    assert (swept / "curation" / "manufacture" / "a_leg" / "pictures" / "b.jpg").is_file()
    assert (swept / "curation" / "neutral" / "a_leg" / "pictures" / "c.jpg").is_file()


def test_a_directory_outside_the_tier_roots_refuses_before_anything_is_read(swept, monkeypatch):
    """The check is at the point of DECIDING, not carried over from whatever
    produced the list. A sweep that trusted its own enumeration would be one
    monkeypatch away from deleting out of the tree."""
    outside = swept.parent / "elsewhere" / "pictures"
    outside.mkdir(parents=True)
    a_pair(outside, "not_ours")
    monkeypatch.setattr(candidate_ledger, "picture_dirs", lambda: [outside])
    candidate_ledger.write([])

    with pytest.raises(candidate_ledger.LedgerError, match="not under either tier root"):
        candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert (outside / "not_ours.jpg").is_file()


def test_a_levelled_colormap_whose_picture_is_gone_is_swept_too(swept):
    """Precisely the pile: 206,147 of these reached 14.9 GiB by outliving pictures
    somebody had already deleted. It is addressed by the name its picture had."""
    pictures = a_leg(swept, "depth", "a_leg", ("in_the_ledger", "half_gone"))
    (pictures / "half_gone.jpg").unlink()
    candidate_ledger.write(
        [a_ledger_row("artifacts/curation/depth/a_leg/pictures/in_the_ledger.jpg")]
    )

    record = candidate_ledger.orphans(apply=True, log=lambda *_: None)

    assert record["named_by_nothing"] == 1
    assert record["pictures"]["colormaps"] == 1
    assert not (pictures / "half_gone.leveled").exists()


def test_the_sweep_deletes_through_the_one_deleter_and_grows_no_second_one():
    """`test_nothing_but_the_ledger_deletes_a_candidate_picture` owns the rule; this
    is the sweep's half of it. A destructive writer that unlinked for itself would
    be a second way to destroy a candidate, past every protection in
    `delete_pictures`."""
    import inspect

    source = inspect.getsource(candidate_ledger.orphans)
    assert "delete_pictures(" in source
    for forbidden in ("unlink(", "rmtree(", "os.remove"):
        assert forbidden not in source, forbidden


def test_by_key_reads_only_the_rows_it_was_asked_for(tmp_path):
    """The lookup a release render makes: a hundred and fifty recipes out of
    hundreds of thousands, without holding the rest."""
    path = tmp_path / "rows.jsonl"
    path.write_text(
        "".join(
            json.dumps({"schema": 1, "key": f"{at:04x}", "picture": None}) + "\n"
            for at in range(50)
        ),
        encoding="utf-8",
        newline="\n",
    )
    found = candidate_ledger.by_key(["0002", "0021"], path)
    assert set(found) == {"0002", "0021"}
    assert candidate_ledger.by_key(["nope"], path) == {}


def test_a_streamed_read_and_a_whole_read_are_the_same_rows(tmp_path):
    """`read` is `stream` collected, so there is one parser and not two."""
    path = tmp_path / "rows.jsonl"
    rows = [{"schema": 1, "key": f"{at:04x}"} for at in range(5)]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    assert list(candidate_ledger.stream(path)) == rows == candidate_ledger.read(path)
    assert list(candidate_ledger.stream(tmp_path / "absent.jsonl")) == []


#: How many stored rows the invariant guard below reads back, and the seed it
#: draws them with. A budget rather than the store, for `tests/README.md`'s
#: reason and with the same arithmetic as `test_hunt.SAMPLE` beside it: reading a
#: recipe back and digesting it is about 0.45 ms, so the whole retained ledger
#: was **55.7 s** on 2026-08-29 over its 122,516 rows — and the store has no
#: ceiling, so that figure grows with every leg. Twenty thousand rows spread over
#: every mode on record is about nine seconds and is the same guard: a `record`
#: and an `of_record` that have drifted have drifted for a whole mode.
RECORD_SAMPLE = 20_000
RECORD_SAMPLE_SEED = 20260829


@pytest.mark.slow
def test_a_sample_of_the_live_ledger_recomputes_each_row_s_own_key(tracked_ledger):
    """**Invariant one, over the store.** `Recipe.record` and `recipes.of_record`
    are inverses on every row that exists, so the store's name for a picture is
    derivable from the row rather than trusted off it.

    This is what lets the row drop `recipe_key`, `regime`, `palette_group` and
    `location`'s copy of the frame: each of them is in the recipe already, and
    this is the assertion that says so over the real store rather than over a
    fixture. `RECORD_SAMPLE` rows at a fixed seed, stratified by mode.
    """
    import random

    by_mode: dict = {}
    for stored in tracked_ledger.rows:
        by_mode.setdefault(str((stored.get("recipe") or {}).get("mode")), []).append(stored)
    draw = random.Random(RECORD_SAMPLE_SEED)
    share = RECORD_SAMPLE / max(1, len(tracked_ledger.rows))
    sampled = [
        stored
        for mode in sorted(by_mode)
        for stored in draw.sample(
            by_mode[mode], min(len(by_mode[mode]), max(1, round(len(by_mode[mode]) * share)))
        )
    ]
    for stored in sampled:
        rebuilt = recipes.of_record(stored["recipe"])
        assert recipes.key_of(rebuilt) == str(stored["key"]), stored["key"]
        # Invariant two rides on the same rebuild: what comes back is an engine
        # spec, so the picture is re-renderable from the row and nothing else.
        assert recipes.of_record(stored["recipe"]).row()["render"]["resolution"]
    assert len(sampled) >= min(RECORD_SAMPLE, len(tracked_ledger.rows)) * 0.9, (
        f"{len(sampled):,} rows drawn against a budget of {RECORD_SAMPLE:,} — a budget that "
        f"is not being filled is coverage given up for nothing"
    )
    assert len(by_mode) > 5, "every mode on record is in the draw"


@pytest.mark.slow
def test_the_live_ledger_s_sidecars_hold_no_row_that_joins_to_nothing(tracked_ledger):
    """A sidecar pruned against a ledger it does not match is rows nothing reads.

    Both sidecars are keyed on the recipe key, and the retention writes all three
    in one transaction precisely so this cannot drift.
    """
    from fractal_wallpapers.curation import flatness

    keys = {str(stored["key"]) for stored in tracked_ledger.rows}
    orphan_scores = {str(row["recipe_key"]) for row in tracked_ledger.scores} - keys
    assert not orphan_scores, f"{len(orphan_scores)} score row(s) join no ledger row"
    orphan_flat = set(flatness.by_recipe()) - keys
    assert not orphan_flat, f"{len(orphan_flat)} flatness row(s) join no ledger row"


# --------------------------------------------------------------------------- #
# Reading the store again on a new judge.
# --------------------------------------------------------------------------- #
def _rescored(isolated, monkeypatch, present, probabilities):
    """`rescore` over `isolated` with the judge and the disk both stubbed."""
    from fractal_wallpapers.curation import colorize, durability
    from fractal_wallpapers.models import scoring, train

    monkeypatch.setattr(candidate_ledger, "partial_scores_path", lambda: isolated / "partial.jsonl")
    monkeypatch.setattr(candidate_ledger, "present_pictures", lambda rows: set(present))
    monkeypatch.setattr(candidate_ledger, "live_artifact", lambda: "new")
    monkeypatch.setattr(colorize, "load_judge", lambda device="auto": (None, {"classes": 4}, "cpu"))
    monkeypatch.setattr(scoring, "transform_of", lambda config: None)
    monkeypatch.setattr(train, "score", lambda *a, **k: probabilities(*a, **k))
    monkeypatch.setattr(durability, "save", lambda durable, log=print: {"stub": True})
    return candidate_ledger.rescore(log=lambda *_: None)


def test_a_rescore_reads_only_what_the_live_judge_has_not_read(isolated, monkeypatch):
    """The retired artifact's rows stay, and a row the live judge has already read
    is not read twice.

    THE shape of the step a judge adoption makes necessary. `scores_by_recipe`
    joins on the live artifact alone, so the morning after a flip the pool is
    empty with a full sidecar — and a pass that rewrote the retired rows, or
    re-read what it had already read, would be answering a different question
    from the one the empty pool asks.
    """
    keys = ["a", "b"]
    rows = []
    for key in keys:
        source = decision()
        rows.append(
            candidate_ledger.row(
                recipe=recipes.of_decision(source),
                key=key,
                source=source,
                picture=str(isolated / f"{key}.jpg"),
            )
        )
    candidate_ledger.write(rows)
    candidate_ledger.write_scores(
        [
            candidate_ledger.score_row(
                key="a",
                artifact="old",
                regime=rows[0]["recipe"]["regime"],
                head="strange_render",
                read={"p_ge2": 0.9, "p_ge3": 0.5, "p_ge4": 0.1, "rank_score": 1.5},
                source={},
            ),
            candidate_ledger.score_row(
                key="a",
                artifact="new",
                regime=rows[0]["recipe"]["regime"],
                head="strange_render",
                read={"p_ge2": 0.9, "p_ge3": 0.6, "p_ge4": 0.2, "rank_score": 1.7},
                source={"scores_current": True},
            ),
        ]
    )
    asked: list = []

    def probabilities(model, paths, transform, where, classes, recipe):
        asked.append(list(paths))
        return [[0.8, 0.7, 0.6] for _ in paths]

    record = _rescored(isolated, monkeypatch, set(keys), probabilities)

    assert record["read"] == 1, "the row the live judge had already read was read again"
    assert len(asked) == 1 and len(asked[0]) == 1
    held = candidate_ledger.read_scores()
    assert len(held) == 3, "the retired artifact's reading was overwritten"
    on_old = [row for row in held if row["judge_artifact"] == "old"]
    assert on_old and on_old[0]["p_ge4"] == 0.1
    fresh = candidate_ledger.scores_by_recipe(held, artifact="new")
    assert set(fresh) == {"a", "b"}
    assert fresh["b"]["p_ge4"] == 0.6 and fresh["b"]["rank_score"] == pytest.approx(2.1)
    assert not candidate_ledger.partial_scores_path().is_file(), (
        "the partial file outlived the pass"
    )


def test_a_rescore_resumes_off_the_chunk_file_it_left_behind(isolated, monkeypatch):
    """A killed pass costs the chunk in flight and nothing before it.

    The finest safe interruption point this leg has: the sidecar is written once,
    at the end, so without the partial file a kill at ninety per cent would ask
    the judge for every picture again.
    """
    source = decision()
    row = candidate_ledger.row(
        recipe=recipes.of_decision(source),
        key="a",
        source=source,
        picture=str(isolated / "a.jpg"),
    )
    candidate_ledger.write([row])
    monkeypatch.setattr(candidate_ledger, "partial_scores_path", lambda: isolated / "partial.jsonl")
    candidate_ledger._append_partial(
        [
            candidate_ledger.score_row(
                key="a",
                artifact="new",
                regime=row["recipe"]["regime"],
                head="strange_render",
                read={"p_ge2": 0.9, "p_ge3": 0.8, "p_ge4": 0.7, "rank_score": 2.4},
                source={"scores_current": True},
            )
        ]
    )

    def refuse(*args, **kwargs):
        raise AssertionError("the judge was asked for a picture the partial file already held")

    record = _rescored(isolated, monkeypatch, {"a"}, refuse)

    assert record["read"] == 1
    assert candidate_ledger.scores_by_recipe(artifact="new")["a"]["p_ge4"] == 0.7
