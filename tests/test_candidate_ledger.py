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
    assert stored["location"]["frame_key"] != stored["location"]["key"]
    assert stored["location"]["agrees"] is False
    assert stored["location"]["superseded_by"] is None
    assert stored["provenance"]["engine"] == candidate_ledger.UNKNOWN_ENGINE


# --------------------------------------------------------------------------- #
# The store.
# --------------------------------------------------------------------------- #
@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """The ledger and its sidecar in a temporary directory, and nothing else touched.

    Four paths and not two. A backfill goes through [`candidate_ledger.merge`],
    which records what it wrote — so an unredirected copy lands on this machine's
    real archive tier and an unredirected manifest lands in the tracked history.
    `tests/test_ledger_tracking.py` owns the rule that makes recording part of the
    write; this is what keeps it inside `tmp_path`.
    """
    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: tmp_path / "rows.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: tmp_path / "scores.jsonl")
    monkeypatch.setattr(candidate_ledger, "backup_path", lambda name: tmp_path / f"copy-{name}")
    monkeypatch.setattr(candidate_ledger, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(candidate_ledger, "_picture_of", lambda source: tmp_path / "nothing.jpg")
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
def test_the_stored_colour_block_is_what_the_picture_still_reads_as():
    """The lens serves the stored block instead of decoding, so the two paths
    have to be one answer. A sample rather than all 85,129 because a decode is
    16 ms a row: this is the guard that catches a drift, not a re-census."""
    import random
    from pathlib import Path

    from fractal_wallpapers.palettes import dominance
    from fractal_wallpapers.paths import rehome

    rows = [
        row
        for row in candidate_ledger.read()
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
