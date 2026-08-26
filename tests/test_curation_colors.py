"""Guard: the colour census describes, and never quietly compares two scales.

The census is a record-and-rank and carries no cut, so what is worth pinning is
not a threshold but the two things that would make its tables mean something
other than what they say:

* the **denominator**. Stage 2's whole point is a pick rate against what was
  actually offered, and a selection ratio computed against the wrong base is a
  statement about the library wearing the head's name.
* the **scale**. A judge's score is calibrated against its own training prior, so
  a stored number from a retired checkpoint is not comparable with a committed
  floor. The census refuses such a row rather than counting it, and this file
  proves the refusal fires.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers.curation import colors, floors, records, rescore
from fractal_wallpapers.palettes import codebook

pytest.importorskip("numpy")
pytest.importorskip("PIL")


def pool_row(run: str, candidate: str, head: str, *, current: dict | None = None, **row) -> dict:
    """One release row with the join a census reads off it."""
    built = records.decision(
        run=run,
        stage=records.RELEASE,
        candidate=candidate,
        verdict=records.RELEASED,
        row={"head": head, "partition": "mandelbrot", "p_ge3": 0.5, **row},
        collection=records.DIAGNOSTIC,
        picture=f"pictures/{candidate}.jpg",
    )
    if current is not None:
        built["scores_current"] = current
    return built


def index_of(rows: list[dict]) -> dict:
    """The pool keyed the way stage 3 keys it, so a `source` chain can be walked."""
    return {row["key"]: row for row in rows}


# --------------------------------------------------------------------------- #
# The scale restriction.
# --------------------------------------------------------------------------- #
def test_a_score_from_another_checkpoint_is_refused_and_not_counted() -> None:
    """The failure this guards is silent: the row has a number, the floor has a
    number, and comparing them produces a rate that looks exactly like a real one."""
    kind = "smooth_render"
    stamp = floors.gallery_floor(kind).stamp
    rows = [
        pool_row("run9", "0001", kind, current={"p_ge3": 0.9, "head_sha256": stamp}),
        pool_row("run9", "0002", kind, current={"p_ge3": 0.9, "head_sha256": "a" * 64}),
    ]
    with pytest.raises(colors.CensusError) as refusal:
        colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
    assert "floor" in str(refusal.value)
    assert "rescore" in str(refusal.value), "a refusal must name the command that fixes it"


def test_rows_on_the_measured_artifact_are_kept_per_kind() -> None:
    smooth, strange = "smooth_render", "strange_render"
    rows = [
        pool_row(
            "run9",
            "0001",
            smooth,
            current={"p_ge3": 0.9, "head_sha256": floors.gallery_floor(smooth).stamp},
        ),
        pool_row(
            "run9",
            "0002",
            strange,
            current={"p_ge3": 0.7, "head_sha256": floors.gallery_floor(strange).stamp},
        ),
    ]
    kept = colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
    assert len(kept[smooth]) == 1
    assert len(kept[strange]) == 1
    assert kept[smooth][0]["score"] == 0.9


# --------------------------------------------------------------------------- #
# The qualification is the ARTIFACT, and never which block the number is in.
# --------------------------------------------------------------------------- #
def written_pass(root: Path, pass_id: str, heads: dict) -> None:
    """One gallery pass's tracked summary, which is where its rows' scale is recorded."""
    directory = root / "gallery" / pass_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pass.json").write_text(
        json.dumps({"config": {"heads": heads}}), encoding="utf-8", newline="\n"
    )


def test_a_row_with_no_current_block_still_counts_when_its_pass_was_the_live_head(
    tmp_path,
) -> None:
    """The defect this pins cost the floor half two thirds of the pool. A gallery
    pass writes `scores_current` onto its release rows and not onto its attempts,
    so gallery3's and gallery4's 10,846 attempt rows carried no such block — while
    their pass records say `config.heads.render` was the artifact shipped today.
    Qualifying on the block refused every one of them for a missing field."""
    kind = "smooth_render"
    stamp = floors.gallery_floor(kind).stamp
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    try:
        written_pass(tmp_path, "gallery9", {"render": stamp[:16]})
        rows = [pool_row("gallery9", "0001", kind)]
        assert rows[0].get("scores_current") is None
        kept = colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
        assert len(kept[kind]) == 1, "a row judged by the live head was refused for a field"
        assert kept[kind][0]["score"] == 0.5
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_a_row_with_no_current_block_from_a_retired_head_is_refused(tmp_path) -> None:
    """The other half of the same rule, and it is the half that has to keep biting:
    a row nobody re-scored, made by a judge that has been replaced, is a number on
    a scale the floor is not on. Silently skipping it is what the old presence
    test did, and a skip says nothing about why the population shrank."""
    kind = "smooth_render"
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    try:
        written_pass(tmp_path, "gallery9", {"render": "a" * 16})
        rows = [pool_row("gallery9", "0001", kind)]
        with pytest.raises(colors.CensusError) as refusal:
            colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
        assert "rescore" in str(refusal.value)
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_a_row_nothing_can_place_is_left_out_rather_than_refused(tmp_path) -> None:
    """A run that left no summary is not evidence of a scale mix — it is evidence
    of a missing record — and refusing the whole census over one would make the
    colour census hostage to something with nothing to do with colour. It is
    reported instead, so the population still says why it is the size it is."""
    kind = "smooth_render"
    records.use(tmp_path)
    rescore._heads_at.cache_clear()
    said: list[str] = []
    try:
        rows = [pool_row("no_such_run", "0001", kind)]
        kept = colors._floor_referenced(rows, index_of(rows), log=said.append)
        assert kept[kind] == []
        assert any("no artifact" in line for line in said), said
    finally:
        records.use(None)
        rescore._heads_at.cache_clear()


def test_an_unscored_row_is_skipped_rather_than_read_as_a_zero() -> None:
    """A render that failed is a decision with a reason and no number. Counting it
    as zero would make a crash indistinguishable from a colour the judge hated."""
    kind = "smooth_render"
    rows = [
        pool_row(
            "run9",
            "0001",
            kind,
            current={"p_ge3": None, "head_sha256": floors.gallery_floor(kind).stamp},
        )
    ]
    assert colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)[kind] == []


def test_one_picture_named_by_a_row_in_each_store_is_counted_once() -> None:
    """The pool's two stores overlap — a gallery pass records its own decision
    about a candidate an earlier run released — and the floor half reads both. A
    picture counted twice weights its colour double in a cell whose whole job is
    to say how often that colour clears."""
    kind = "smooth_render"
    stamp = floors.gallery_floor(kind).stamp
    released = pool_row("run9", "0001", kind, current={"p_ge3": 0.9, "head_sha256": stamp})
    seated = pool_row("gallery1", "run9_0001", kind, current={"p_ge3": 0.9, "head_sha256": stamp})
    seated["source"] = {"key": released["key"], "run": "run9", "candidate": "0001"}
    rows = [released, seated]

    kept = colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
    assert len(kept[kind]) == 1
    assert kept[kind][0]["picture"].endswith("0001.jpg")


def test_a_pass_over_a_pass_resolves_to_the_run_that_rendered_it() -> None:
    """One hop lands on a path nobody ever wrote, and the census reported that
    render as absent rather than as the colour it is."""
    kind = "strange_render"
    stamp = floors.gallery_floor(kind).stamp
    made = pool_row("run9", "0008", kind, current={"p_ge3": 0.7, "head_sha256": stamp})
    # Every row on the measured artifact, because the chain is what this pins and a
    # link on a retired scale is refused by the rule above before the walk starts.
    once = pool_row("gallery1", "run9_0008", kind, current={"p_ge3": 0.7, "head_sha256": stamp})
    once["source"] = {"key": made["key"], "run": "run9", "candidate": "0008"}
    twice = pool_row(
        "gallery2", "gallery1_0003", kind, current={"p_ge3": 0.7, "head_sha256": stamp}
    )
    twice["source"] = {"key": once["key"], "run": "gallery1", "candidate": "run9_0008"}
    rows = [made, once, twice]

    kept = colors._floor_referenced(rows, index_of(rows), log=lambda *a: None)
    resolved = {cell["picture"] for cell in kept[kind]}
    assert len(resolved) == 1
    assert next(iter(resolved)).endswith(str(Path("run9") / "pictures" / "0008.jpg"))


# --------------------------------------------------------------------------- #
# The metrics.
# --------------------------------------------------------------------------- #
def test_both_thresholds_are_always_reported() -> None:
    """The 25% cell is expected to be sparse; that sparsity is the reading, so it
    may never be dropped for being small."""
    vectors = [{"dark_vivid_green": 0.30}, {"dark_vivid_green": 0.15}, {"black": 0.9}]
    table = colors.thresholded(vectors)
    assert table["n"] == 3
    cell = table["swatches"]["dark_vivid_green"]
    assert cell["at_10pct"] == 2
    assert cell["at_25pct"] == 1
    assert cell["present_share_mean"] == pytest.approx(0.15, abs=1e-6)
    assert set(table["swatches"]) == set(codebook.names())


def test_a_swatch_nothing_reaches_is_reported_as_zero_and_not_omitted() -> None:
    """An absent row and a zero row read the same in a table and mean opposite
    things: one is a colour nothing carried, the other is a colour nobody asked
    about."""
    table = colors.thresholded([{"black": 1.0}])
    assert table["swatches"]["dark_vivid_green"]["at_10pct"] == 0
    assert table["swatches"]["dark_vivid_green"]["present_share_mean"] == 0.0


def test_families_fold_the_fifty_two_onto_thirteen_cells() -> None:
    rows = [
        {"dominant": "dark_vivid_green"},
        {"dominant": "light_muted_green"},
        {"dominant": "black"},
    ]
    assert colors._families(rows) == {"green": 2, "neutral": 1}


def test_the_spread_of_nothing_is_null_rather_than_zero() -> None:
    """A cell with no candidates has no median, and a zero there would sort as the
    worst-scoring colour in the table."""
    assert colors._spread([]) == {"mean": None, "median": None}
    assert colors._spread([1.0, 3.0])["median"] == 2.0


# --------------------------------------------------------------------------- #
# Stage 2's denominator.
# --------------------------------------------------------------------------- #
def test_the_selection_ratio_is_against_what_was_offered(monkeypatch) -> None:
    """One colour offered in every set and taken every time is over-picked by the
    full factor of the set size; the same colour taken at chance is 1.0."""
    maps = [
        {"colormap": "greenish", "shares": {"dark_vivid_green": 0.5}},
        {"colormap": "reddish", "shares": {"dark_vivid_red": 0.5}},
    ]
    rows = [
        pool_row("run9", f"{index:04d}", "smooth_render", colormap="greenish") for index in range(4)
    ]
    for row in rows:
        row["palette"] = {"candidates": ["greenish", "reddish"], "anchor": "greenish"}
        row["recipe"]["colormap"] = "greenish"
    monkeypatch.setattr(colors, "_pool_rows", lambda: rows)
    table, built = colors.picks(maps, log=lambda *a: None)

    assert table["sets"] == 4
    green = table["swatches"]["dark_vivid_green"]
    red = table["swatches"]["dark_vivid_red"]
    assert green["offered"] == 4 and green["picked"] == 4
    assert red["offered"] == 4 and red["picked"] == 0
    # Four offers over a nominal set of 32 is an eighth of an expected pick.
    assert green["expected_if_blind"] == pytest.approx(0.125)
    assert green["selection_ratio"] == pytest.approx(32.0)
    assert red["selection_ratio"] == 0.0
    assert len(built) == 4


def test_a_set_naming_a_map_the_library_does_not_hold_is_skipped_and_counted(monkeypatch) -> None:
    """Silently dropping it would shrink the denominator without saying so."""
    maps = [{"colormap": "greenish", "shares": {"dark_vivid_green": 0.5}}]
    row = pool_row("run9", "0001", "smooth_render")
    row["palette"] = {"candidates": ["greenish", "vanished"], "anchor": "greenish"}
    row["recipe"]["colormap"] = "greenish"
    monkeypatch.setattr(colors, "_pool_rows", lambda: [row])
    table, built = colors.picks(maps, log=lambda *a: None)
    assert table["sets"] == 0
    assert table["skipped_unknown_map"] == 1
    assert built == []


# --------------------------------------------------------------------------- #
# The artifact.
# --------------------------------------------------------------------------- #
def test_the_manifest_describes_the_rows_rather_than_holding_them(tmp_path, monkeypatch) -> None:
    """The rows are megabytes against a 1 MiB per-file history guard, so what the
    history keeps is a measurement of them."""
    monkeypatch.setattr(colors, "census_dir", lambda: tmp_path / "artifacts")
    monkeypatch.setattr(colors, "manifest_path", lambda: tmp_path / "data" / "manifest.json")
    readout = colors.take(stages=("library",), log=lambda *a: None)

    assert readout["baseline"] == colors.BASELINE
    assert readout["stages"]["library"]["maps"] > 600
    manifest = json.loads((tmp_path / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["rows"]["rows"] == readout["stages"]["library"]["maps"]
    assert len(manifest["rows"]["sha256"]) == 64
    assert manifest["stages"] == ["library"]
    assert manifest["rebuild_command"].startswith("fractal-wallpapers curate colors")
    assert (tmp_path / "data" / "manifest.json").stat().st_size < 1_048_576


def test_the_artifact_carries_the_codebook_that_produced_it(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(colors, "census_dir", lambda: tmp_path / "artifacts")
    monkeypatch.setattr(colors, "manifest_path", lambda: tmp_path / "manifest.json")
    colors.take(stages=("library",), log=lambda *a: None)
    written = json.loads((tmp_path / "artifacts" / "census.json").read_text(encoding="utf-8"))
    assert len(written["codebook"]["swatches"]) == 52
    assert written["codebook"]["assignment"]["sigma"] == 0.015


def test_an_unknown_stage_is_refused_rather_than_silently_doing_nothing() -> None:
    with pytest.raises(colors.CensusError):
        colors.take(stages=("colour",), log=lambda *a: None)


def test_a_partial_run_carries_the_other_stages_instead_of_deleting_them(
    tmp_path, monkeypatch
) -> None:
    """`--stage library` recomputes a quarter of the census. Writing only that
    quarter would throw the other three away, which is the mistake `intake` upserts
    to avoid."""
    monkeypatch.setattr(colors, "census_dir", lambda: tmp_path / "artifacts")
    monkeypatch.setattr(colors, "manifest_path", lambda: tmp_path / "manifest.json")

    def fake_picks(map_rows, log=print):
        return {"sets": 7}, [{"schema": 1, "stage": "picks", "chosen": "somemap"}]

    monkeypatch.setattr(colors, "picks", fake_picks)
    both = colors.take(stages=("library", "picks"), log=lambda *a: None)
    maps = both["stages"]["library"]["maps"]
    assert set(both["stages"]) == {"library", "picks"}

    again = colors.take(stages=("library",), log=lambda *a: None)
    assert set(again["stages"]) == {"library", "picks"}, "the picks stage was deleted"
    assert again["stages"]["picks"]["sets"] == 7

    rows = (tmp_path / "artifacts" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    stages = [json.loads(line)["stage"] for line in rows if line.strip()]
    assert stages.count("picks") == 1, "the carried stage's rows were lost or doubled"
    assert stages.count("library") == maps

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stages_this_run"] == ["library"]
    assert [entry["stage"] for entry in manifest["stages_carried"]] == ["picks"]


def test_a_carried_stage_keeps_the_date_it_was_actually_computed(tmp_path, monkeypatch) -> None:
    """A table dated today, derived from a pool that has since grown, with nothing
    on it to say so, is worse than a visibly stale one."""
    monkeypatch.setattr(colors, "census_dir", lambda: tmp_path / "artifacts")
    monkeypatch.setattr(colors, "manifest_path", lambda: tmp_path / "manifest.json")
    monkeypatch.setattr(
        colors, "picks", lambda map_rows, log=print: ({"sets": 1}, [{"stage": "picks"}])
    )
    first = colors.take(stages=("library", "picks"), log=lambda *a: None)
    when = first["stage_taken_at"]["picks"]

    monkeypatch.setattr(colors, "datetime", _later(colors.datetime))
    second = colors.take(stages=("library",), log=lambda *a: None)
    assert second["stage_taken_at"]["picks"] == when
    assert second["stage_taken_at"]["library"] != when


def _later(real):
    class Clock:
        UTC = real.now().tzinfo

        @staticmethod
        def now(tz=None):
            from datetime import timedelta

            return real.now(tz) + timedelta(days=1)

    return Clock


def test_a_stage_table_is_never_given_metadata_of_its_own(tmp_path, monkeypatch) -> None:
    """The `labels` table is keyed by head and nothing else, so a timestamp written
    into it puts a string where every reader expects a cell. The stamps live in
    `stage_taken_at` beside the tables for exactly that reason."""
    monkeypatch.setattr(colors, "census_dir", lambda: tmp_path / "artifacts")
    monkeypatch.setattr(colors, "manifest_path", lambda: tmp_path / "manifest.json")
    monkeypatch.setattr(
        colors, "picks", lambda map_rows, log=print: ({"sets": 1}, [{"stage": "picks"}])
    )
    monkeypatch.setattr(
        colors, "labels", lambda log=print: ({"smooth_render": {"pictures": 3}}, [])
    )
    readout = colors.take(stages=("library", "picks", "labels"), log=lambda *a: None)
    assert set(readout["stages"]["labels"]) == {"smooth_render"}
    assert set(readout["stage_taken_at"]) == {"library", "picks", "labels"}

    again = colors.take(stages=("library",), log=lambda *a: None)
    assert set(again["stages"]["labels"]) == {"smooth_render"}, "a carried table was polluted"
    for head, cell in again["stages"]["labels"].items():
        assert isinstance(cell, dict), f"{head} is not a cell"
