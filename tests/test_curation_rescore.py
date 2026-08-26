"""Reading the accumulated pool through today's heads, without losing what a run read.

Two of six runs were judged by a strange head that has since been replaced by a
four-class one. Their rows have no `P(≥4)` at all and their `P(≥3)` is a point on
a scale that no longer exists — which is fine for a record of what a run decided
and useless for a comparison across runs. The re-read gives every row a number on
the live scale and leaves the run's own reading exactly where it is.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import durability, gallery_store, records, rescore
from fractal_wallpapers.curation import run as run_module


def released(run: str, candidate: str, head: str, **scores) -> dict:
    row = records.decision(
        run=run,
        stage=records.RELEASE,
        candidate=candidate,
        verdict=records.RELEASED,
        row={"head": head, "partition": "mandelbrot", **scores},
        collection=records.DIAGNOSTIC,
        picture=f"release/{candidate}.png",
    )
    return row


# --------------------------------------------------------------------------- #
# Which picture, and which head.
# --------------------------------------------------------------------------- #
def test_the_picture_is_the_candidate_render_and_not_the_release_png() -> None:
    """One geometry for every row, or the readings are not comparable. Only 153 of
    the 1,050 rows have a release render, and `row["picture"]` is three different
    things depending on the verdict."""
    row = released("run9", "0007", "smooth_render")
    where = rescore.picture_of(row)
    assert where.name == "0007.jpg"
    assert where.parent == run_module.run_dir("run9") / rescore.PICTURES
    assert where.parent.name == "pictures"


def test_a_gallery_seat_reads_the_picture_of_the_run_that_made_it() -> None:
    """A pass records its own decision about an earlier run's candidate, under its
    own id. The picture is still that run's, and `source` is what says so."""
    row = released("gallery1", "run9_0007", "smooth_render")
    row["source"] = {"run": "run9", "candidate": "0007", "key": "run9|release|0007"}
    where = rescore.picture_of(row)
    assert where.name == "0007.jpg"
    assert where.parent == run_module.run_dir("run9") / rescore.PICTURES


@pytest.fixture
def isolated_pool(tmp_path, monkeypatch):
    """Both halves of the pool under `tmp_path`: the tracked store and the pass stores."""
    monkeypatch.setattr(gallery_store, "store_root", lambda: tmp_path / "gallery_store")
    monkeypatch.setattr(
        gallery_store,
        "backup_path",
        lambda pass_id: tmp_path / "backup" / str(pass_id) / gallery_store.STORE_NAME,
    )
    monkeypatch.setattr(durability, "rehome", lambda stored: None)
    records.use(tmp_path)
    yield tmp_path
    records.use(None)


def test_a_row_naming_no_kind_refuses_rather_than_being_guessed_at(isolated_pool) -> None:
    """A candidate belongs to the judge whose slots paid for it. Reading a strange
    picture through the smooth head produces a number about material that head has
    never seen."""
    records.write_decisions(
        records.RELEASE,
        "r",
        [
            records.decision(
                run="r",
                stage=records.RELEASE,
                candidate="0000",
                verdict=records.PASSED_OVER,
                # Scored, and naming no head: an unscored row is skipped before
                # this refusal can act, and would test nothing.
                row={"partition": "mandelbrot", "p_ge3": 0.5},
                collection=records.DIAGNOSTIC,
            )
        ],
    )
    with pytest.raises(rescore.RescoreError, match="names no kind"):
        rescore.run(log=lambda *_: None)


def test_an_empty_store_refuses(isolated_pool) -> None:
    with pytest.raises(rescore.RescoreError, match="no scored row"):
        rescore.run(log=lambda *_: None)


# --------------------------------------------------------------------------- #
# Which artifact actually scored a row.
# --------------------------------------------------------------------------- #
def test_the_scoring_artifact_comes_off_the_run_record_and_not_off_the_row(
    tmp_path,
) -> None:
    """A row carries `bar.head_sha256`, and on a gated head that is the artifact
    the BAR was measured against rather than the one that scored the row —
    `floors.release_cut` builds it that way deliberately. Reading bar provenance
    as score provenance is how a scale shift goes unnoticed."""
    records.use(tmp_path)
    try:
        runs = tmp_path / "runs"
        runs.mkdir(parents=True)
        (runs / "r.json").write_text(
            json.dumps({"config": {"heads": {"strange_render": "a011188bbcaaeef4"}}}),
            encoding="utf-8",
            newline="\n",
        )
        assert rescore.scoring_artifact("r") == {"strange_render": "a011188bbcaaeef4"}
        assert rescore.scoring_artifact("never_ran") == {}
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_a_gallery_passs_scale_comes_off_its_own_summary(tmp_path) -> None:
    """A pass books no clock and is not filed under `runs/`, so a lookup that knew
    only that directory read every pass row's provenance as absent — which is a
    different wrong answer from the one this lookup exists to prevent, and just as
    quiet. Both places are tried."""
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    try:
        directory = tmp_path / "gallery" / "gallery9"
        directory.mkdir(parents=True)
        (directory / "pass.json").write_text(
            json.dumps({"config": {"heads": {"render": "e62e8dbab7f47ffe"}}}),
            encoding="utf-8",
            newline="\n",
        )
        assert rescore.scoring_artifact("gallery9") == {"render": "e62e8dbab7f47ffe"}
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_a_bar_stamp_is_never_read_as_the_artifact_that_scored_the_row(tmp_path) -> None:
    """`bar.head_sha256` is the artifact the BAR's height was measured on, which
    `floors.release_cut` builds that way deliberately. On gallery4's rows it
    happens to equal the live judge; on run10's it happened to equal that night's.
    Reading it as score provenance is right by coincidence twice and wrong the
    first time the two come apart."""
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    try:
        runs = tmp_path / "runs"
        runs.mkdir(parents=True)
        (runs / "r.json").write_text(
            json.dumps({"config": {"heads": {"strange_render": "a011188bbcaaeef4"}}}),
            encoding="utf-8",
            newline="\n",
        )
        row = records.decision(
            run="r",
            stage=records.RELEASE,
            candidate="0001",
            verdict=records.RELEASED,
            row={
                "head": "strange_render",
                "partition": "mandelbrot",
                "p_ge3": 0.9,
                "bar": {"name": "strange_render_release", "value": 0.575, "head_sha256": "z" * 64},
            },
        )
        assert rescore.artifact_of(row) == "a011188bbcaaeef4"
        assert rescore.reading_on(row, "z" * 64) is None
        assert rescore.reading_on(row, "a011188bbcaaeef4dead")["p_ge3"] == 0.9
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_a_current_block_outranks_the_run_record(tmp_path) -> None:
    """A re-scored row says on itself which artifact re-read it, and that is a
    stronger statement than what the run was scored by on the night it ran."""
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    try:
        runs = tmp_path / "runs"
        runs.mkdir(parents=True)
        (runs / "r.json").write_text(
            json.dumps({"config": {"heads": {"smooth_render": "a011188bbcaaeef4"}}}),
            encoding="utf-8",
            newline="\n",
        )
        row = records.decision(
            run="r",
            stage=records.RELEASE,
            candidate="0001",
            verdict=records.RELEASED,
            row={"head": "smooth_render", "partition": "mandelbrot", "p_ge3": 0.1},
        )
        row["scores_current"] = {"p_ge3": 0.9, "head_sha256": "e" * 64}
        assert rescore.artifact_of(row) == "e" * 64
        assert rescore.reading_on(row, "e" * 64)["p_ge3"] == 0.9
        assert rescore.reading_on(row, "a011188bbcaaeef4") is None
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


# --------------------------------------------------------------------------- #
# The tracked pool, after the pass.
# --------------------------------------------------------------------------- #
def test_every_pool_row_carries_a_reading_on_the_live_judge() -> None:
    """The block keeps the row's KIND under `head` — every consumer reads it to
    pick a floor and a slot — and names the one judge that produced the numbers
    under `judge`, stamped with that judge's artifact."""
    from fractal_wallpapers.curation import floors

    rows = records.read_decisions(records.RELEASE)
    missing = [row["key"] for row in rows if not row.get(rescore.BLOCK)]
    if missing:
        pytest.skip(f"{len(missing)} rows have not been re-read in this checkout")
    live = floors.live_stamp(floors.SCORING_HEAD)
    for row in rows:
        block = row[rescore.BLOCK]
        assert block["head"] == row["scores"]["head"]
        assert block["judge"] == floors.SCORING_HEAD
        assert block["head_sha256"] == live
        assert 0.0 <= block["p_ge3"] <= 1.0


def test_every_writer_of_the_block_writes_the_same_shape() -> None:
    """Two passes write `scores_current` — the re-score, and the gallery pass for
    its own attempts — and a field missing from one of them makes the pool two
    shapes. It did: the gallery writer built the block itself and left `judge`
    off, so a reader that asked for it worked on every row but the ones one pass
    had made. Both go through `rescore.block` now, and this is what says so."""
    from fractal_wallpapers.curation import floors

    built = rescore.block("smooth_render", {"p_ge2": 0.9, "p_ge3": 0.8, "p_ge4": 0.7})
    assert built["head"] == "smooth_render"
    assert built["judge"] == floors.SCORING_HEAD
    assert built["head_sha256"] == floors.live_stamp(floors.SCORING_HEAD)
    assert built["rank_score"] is None, "a reading the caller did not have stays absent"

    rows = records.read_decisions(records.RELEASE)
    blocks = [row[rescore.BLOCK] for row in rows if row.get(rescore.BLOCK)]
    assert blocks
    shape = set(built)
    for block in blocks:
        assert set(block) == shape


def test_the_runs_own_scores_are_untouched_provenance() -> None:
    """`scores` is what the decision was actually taken on. A pass that overwrote
    it would delete the only evidence of what the release path decided."""
    rows = records.read_decisions(records.RELEASE)
    if not any(row.get(rescore.BLOCK) for row in rows):
        pytest.skip("the pool has not been re-read in this checkout")
    retired = [row for row in rows if row["scores"].get("p_ge4") is None]
    assert retired, "the two runs on the retired three-class head are still on record"
    for row in retired:
        # The old reading kept its shape: three classes, so no fourth cutpoint.
        assert row["scores"]["p_ge4"] is None
        # And the new one has one, which is the whole point of the pass.
        assert row[rescore.BLOCK]["p_ge4"] is not None


def test_a_reading_never_lands_where_a_cut_would_read_it_by_accident() -> None:
    """The block is beside `scores`, not inside it. Every cut in curation reads
    `scores.p_ge3`, and a pass that wrote the live number there would silently
    re-decide six runs' worth of records."""
    rows = records.read_decisions(records.RELEASE)
    if not any(row.get(rescore.BLOCK) for row in rows):
        pytest.skip("the pool has not been re-read in this checkout")
    assert rescore.BLOCK != "scores"
    for row in rows[:50]:
        assert set(row["scores"]) == {
            "head",
            "location_p_ge3",
            "p_ge2",
            "p_ge3",
            "p_ge4",
            "rank_score",
        }


def test_a_reading_goes_back_to_the_store_the_row_came_from(isolated_pool) -> None:
    """A pass's attempts are not in the history, and a re-score must not put them there."""
    attempt = records.decision(
        run="gallery1",
        stage=records.GATE,
        candidate="0007",
        verdict="kept",
        row={"partition": "mandelbrot", "head": "smooth_render", "p_ge3": 0.5},
    )
    seat = records.decision(
        run="gallery1",
        stage=records.RELEASE,
        candidate="0007",
        verdict=records.RELEASED,
        collection=records.GALLERY,
        row={"partition": "mandelbrot", "head": "smooth_render", "p_ge3": 0.5},
        picture="release/0007.png",
    )
    gallery_store.write("gallery1", [attempt])
    records.write_decisions(records.RELEASE, "gallery1", [seat])
    block = {"head": "smooth_render", "p_ge3": 0.9}

    written = rescore._write([attempt, seat], {attempt["key"]: block, seat["key"]: block}, print)

    assert written == {"gallery1/gate": 1, "gallery1/release": 1}
    assert gallery_store.read("gallery1")[0][rescore.BLOCK] == block
    tracked = records.read_decisions(records.RELEASE, "gallery1")
    assert [row["candidate"] for row in tracked] == ["0007"]
    assert tracked[0][rescore.BLOCK] == block
    # The manifest was saved again in the same call, so the store still reads whole.
    assert gallery_store.check("gallery1", log=lambda _line: None)["verdict"] == "ok"
