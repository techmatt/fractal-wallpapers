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
    """
    from fractal_wallpapers.curation import flatness

    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: tmp_path / "rows.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: tmp_path / "scores.jsonl")
    monkeypatch.setattr(candidate_ledger, "backup_path", lambda name: tmp_path / f"copy-{name}")
    monkeypatch.setattr(candidate_ledger, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(candidate_ledger, "_picture_of", lambda source: tmp_path / "nothing.jpg")
    monkeypatch.setattr(flatness, "sidecar_path", lambda: tmp_path / "flatness.jsonl")
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

    The bound is `RETAIN_PER_PAIR` *plus whatever the four protections carry*, and
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


def test_nothing_but_the_ledger_deletes_a_candidate_picture():
    """One delete in this project, in one module, reachable from one function."""
    import inspect

    from fractal_wallpapers.curation import retention

    assert "unlink(" not in inspect.getsource(retention)
    unlinks = [
        name
        for name, held in vars(candidate_ledger).items()
        if inspect.isfunction(held)
        and held.__module__ == candidate_ledger.__name__
        and "unlink(" in inspect.getsource(held)
    ]
    assert sorted(unlinks) == ["delete_pictures", "prune"], unlinks


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
