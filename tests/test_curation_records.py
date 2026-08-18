"""The release records: the join on one row, the denominator beside it, one binding."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import records


@pytest.fixture(autouse=True)
def unbound():
    """Every test starts and ends with the durable store bound, like a run does."""
    records.use(None)
    yield
    records.use(None)


def candidate_row(**extra) -> dict:
    return {
        "key": '["mandelbrot", 2, [], "-0.5", "0", "0.4"]',
        "partition": "mandelbrot",
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.5", "center_im": "0", "width": "0.4"},
        "maxiter": 500,
        "mode": "smooth",
        "mode_kind": "field",
        "curve": "linear",
        "colormap": "viridis",
        "mirror": True,
        "head": "smooth_render",
        "p_ge3": 0.8,
        "anchor": "viridis",
        "candidates": ["viridis", "magma"],
        **extra,
    }


def test_a_row_carries_the_whole_join_it_was_decided_on() -> None:
    """A row keyed on an identifier whose meaning lives elsewhere is orphaned the
    day that file moves."""
    row = records.decision(
        run="r",
        stage=records.RELEASE,
        candidate="0001",
        verdict="released",
        row=candidate_row(),
        slot_source="mix",
        group="group#3",
    )
    assert row["location"]["family"] == {"kind": "mandelbrot"}
    assert row["recipe"]["colormap"] == "viridis"
    assert row["scores"]["p_ge3"] == 0.8
    assert row["palette"]["candidates"] == ["viridis", "magma"]


def test_a_row_that_took_no_slot_has_no_slot_provenance() -> None:
    """Defaulting it to the mix would invent a decision nobody made."""
    row = records.decision(
        run="r",
        stage=records.RELEASE,
        candidate="0002",
        verdict="passed_over",
        row=candidate_row(),
    )
    assert row["slot_source"] is None


def test_a_failed_render_records_a_reason_and_no_score() -> None:
    """Recording it as a zero would make a crash indistinguishable from a bad wallpaper."""
    row = records.decision(
        run="r",
        stage=records.GATE,
        candidate="0003",
        verdict="dropped",
        row=candidate_row(p_ge3=None, error="engine failed"),
        reason="engine failed",
    )
    assert row["scores"]["p_ge3"] is None
    assert row["reason"] == "engine failed"


def test_the_population_carries_the_whole_funnel_not_just_the_survivors() -> None:
    row = records.population(
        run="r",
        ledgers=["a/walk.jsonl"],
        counts={"found": 100, "released": 6},
        cuts={},
        config={},
    )
    assert row["counts"]["found"] == 100


def test_a_re_run_is_idempotent_and_a_second_run_is_additive(tmp_path) -> None:
    records.use(tmp_path)
    first = [
        records.decision(
            run="a",
            stage=records.GATE,
            candidate="0000",
            verdict="kept",
            row=candidate_row(),
        )
    ]
    path, total, new = records.write_decisions(records.GATE, "a", first)
    assert (total, new) == (1, 1)
    before = path.read_bytes()

    _, total, new = records.write_decisions(records.GATE, "a", first)
    assert (total, new) == (1, 0)
    assert path.read_bytes() == before

    second = [
        records.decision(
            run="b",
            stage=records.GATE,
            candidate="0000",
            verdict="kept",
            row=candidate_row(),
        )
    ]
    other, total, new = records.write_decisions(records.GATE, "b", second)
    assert (total, new) == (1, 1)
    assert other != path
    # Additive, and now structurally so: the second run wrote its own file and the
    # first run's bytes are the ones it wrote.
    assert path.read_bytes() == before
    assert len(records.read_decisions(records.GATE)) == 2
    keys = [json.loads(line)["key"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert keys == sorted(keys)


def test_a_run_writes_one_file_of_its_own_at_each_stage(tmp_path) -> None:
    """The shard axis is the run, because it was already the key's axis.

    A store that accumulated every run into one file grew for as long as the
    project did — 918 KiB against the 1 MiB history guard by the third run — and
    the fix is not a smaller row but a file whose ceiling is one run's rows.
    """
    records.use(tmp_path)
    for run in ("a", "b"):
        for stage in (records.GATE, records.RELEASE):
            records.write_decisions(
                stage,
                run,
                [
                    records.decision(
                        run=run,
                        stage=stage,
                        candidate="0000",
                        verdict="kept",
                        row=candidate_row(),
                    )
                ],
            )
    assert sorted(path.name for path in (tmp_path / records.GATE).glob("*.jsonl")) == [
        "a.jsonl",
        "b.jsonl",
    ]
    assert not (tmp_path / "gate.jsonl").exists()
    assert records.decisions_path(records.RELEASE, "a") == tmp_path / "release" / "a.jsonl"


def test_the_unified_reader_is_the_whole_store_in_key_order(tmp_path) -> None:
    """A store split across runs is still one logical store, and every consumer
    reads it through here rather than knowing how many files it is."""
    records.use(tmp_path)
    for run in ("b", "a", "c"):
        records.write_decisions(
            records.RELEASE,
            run,
            [
                records.decision(
                    run=run,
                    stage=records.RELEASE,
                    candidate=candidate,
                    verdict="released",
                    row=candidate_row(),
                )
                for candidate in ("0001", "0000")
            ],
        )
    rows = records.read_decisions(records.RELEASE)
    assert len(rows) == 6
    keys = [row["key"] for row in rows]
    assert keys == sorted(keys)
    assert [row["run"] for row in records.read_decisions(records.RELEASE, "b")] == ["b", "b"]
    assert records.read_decisions(records.RELEASE, "nobody") == []


def test_the_ephemeral_binding_moves_the_whole_store(tmp_path) -> None:
    """One binding at the run's entry point: a redirect applied at three of four
    sites is not a redirect."""
    records.use(tmp_path / "elsewhere")
    assert records.is_durable() is False
    assert all(
        tmp_path in path.parents or path.is_relative_to(tmp_path)
        for path in records.sinks("r").values()
    )
    records.assert_isolated("r")


def test_a_run_declared_ephemeral_that_resolves_under_data_is_refused() -> None:
    """The stores accumulate by run id, so a rehearsal does not overwrite a row —
    it adds rows a later calibration pass cannot tell from a release's."""
    records.use(records.default_root())
    with pytest.raises(records.NotIsolated):
        records.assert_isolated("r")


def test_the_scratch_root_is_keyed_by_run() -> None:
    """Two rehearsals sharing a root would upsert into each other's record."""
    assert records.scratch_root("a") != records.scratch_root("b")
    assert "scratch" in records.scratch_root("a").parts


def test_the_read_side_exists_so_the_record_can_be_read(tmp_path) -> None:
    records.use(tmp_path)
    rows = [
        records.decision(
            run=run,
            stage=records.RELEASE,
            candidate="0000",
            verdict="released",
            row=candidate_row(),
        )
        for run in ("a", "b")
    ]
    for row in rows:
        records.write_decisions(records.RELEASE, row["run"], [row])
    assert len(records.read_decisions(records.RELEASE)) == 2
    assert len(records.read_decisions(records.RELEASE, "a")) == 1
