"""The release records: the join on one row, the denominator beside it, one binding."""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import records


@pytest.fixture(autouse=True)
def unbound():
    """Every test starts and ends with the durable store bound, like a run does."""
    records.use(None)
    yield
    records.use(None)


def _bytes(directory) -> dict:
    """Every file under one run's decision directory, by name. What "byte for byte"
    means once a run's rows are more than one file."""
    return {path.name: path.read_bytes() for path in sorted(directory.glob("*.jsonl"))}


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


def _release_row(candidate: str, seated: bool, picture) -> dict:
    """One release row exactly as a run writes it, verdict and all."""
    from fractal_wallpapers.curation import run as run_module

    verdict, reason = run_module.release_verdict(seated, picture)
    # The gate render this decision was taken on. On disk, and it resolves.
    candidate_picture = f"pictures/{candidate}.jpg"
    return records.decision(
        run="r",
        stage=records.RELEASE,
        candidate=candidate,
        verdict=verdict,
        row=candidate_row(picture=candidate_picture),
        reason=reason,
        picture=None if verdict == records.KILLED else (picture or candidate_picture),
    )


def test_a_row_whose_release_render_was_killed_is_not_served() -> None:
    """run3: two seated rows, no full-resolution picture, and `verdict: released`.

    The candidate JPEG the gate decision was taken on is a 640x360 thumbnail, it is
    on disk and it resolves, so a listing that read the verdict alone served it as
    the wallpaper.
    """
    made = _release_row("0001", True, "release/0001.png")
    killed = _release_row("0002", True, None)
    assert killed["verdict"] == records.KILLED
    assert killed["picture"] is None, "nothing may resolve to the gate render"
    assert killed["reason"] == records.KILLED_REASON
    assert [row["candidate"] for row in records.served([made, killed])] == ["0001"]

    # A row that took no slot keeps its candidate render — that is what the sheet
    # shows a near miss with — and is not served either.
    passed = _release_row("0003", False, None)
    assert passed["verdict"] == records.PASSED_OVER
    assert passed["picture"] == "pictures/0003.jpg"
    assert records.served([passed]) == []

    # Belt and braces: `served` checks the verdict and the pointer separately, so a
    # row that somehow kept one of the two is still not served.
    assert records.served([{**killed, "verdict": records.RELEASED}]) == []
    assert records.served([{**made, "picture": None}]) == []


def test_a_killed_row_flips_back_through_the_upsert_when_the_picture_is_made(tmp_path) -> None:
    """The re-render is a state change on the same key, not a second row."""
    records.use(tmp_path)
    records.write_decisions(records.RELEASE, "r", [_release_row("0002", True, None)])
    records.write_decisions(records.RELEASE, "r", [_release_row("0002", True, "release/0002.png")])

    rows = records.read_decisions(records.RELEASE, "r")
    assert len(rows) == 1
    assert rows[0]["verdict"] == records.RELEASED
    assert [row["candidate"] for row in records.served(rows)] == ["0002"]


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
    directory, total, new = records.write_decisions(records.GATE, "a", first)
    assert (total, new) == (1, 1)
    before = _bytes(directory)

    _, total, new = records.write_decisions(records.GATE, "a", first)
    assert (total, new) == (1, 0)
    assert _bytes(directory) == before

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
    assert other != directory
    # Additive, and now structurally so: the second run wrote its own directory and
    # the first run's bytes are the ones it wrote.
    assert _bytes(directory) == before
    assert len(records.read_decisions(records.GATE)) == 2
    keys = [row["key"] for row in records.read_decisions(records.GATE, "a")]
    assert keys == sorted(keys)


def test_a_run_writes_a_file_per_partition_under_a_directory_of_its_own(tmp_path) -> None:
    """Neither shard axis is invented for the filesystem's sake.

    The run was already the key's axis and the partition is the axis every
    apportionment is taken on. Accumulated into one file per stage the store grew
    for as long as the project did — 918 KiB against the 1 MiB history guard by the
    third run — and one file per run alone was still 828 KiB after a 240-attempt
    run. The fix is not a smaller row.
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
                        candidate=f"000{index}",
                        verdict="kept",
                        row=candidate_row(partition=partition),
                    )
                    for index, partition in enumerate(("mandelbrot", "julia:mandelbrot"))
                ],
            )
    assert sorted(path.name for path in (tmp_path / records.GATE / "a").glob("*.jsonl")) == [
        "julia_mandelbrot.jsonl",
        "mandelbrot.jsonl",
    ]
    assert not (tmp_path / "gate.jsonl").exists()
    assert not (tmp_path / "gate" / "a.jsonl").exists()
    assert (
        records.decisions_path(records.RELEASE, "a", "julia:multibrot3")
        == tmp_path / "release" / "a" / "julia_multibrot3.jsonl"
    )


def test_a_partition_left_with_no_rows_loses_its_file(tmp_path) -> None:
    """The listing is the partitions the run decided in, not the ones it once did."""
    records.use(tmp_path)

    def write(partition):
        records.write_decisions(
            records.GATE,
            "a",
            [
                records.decision(
                    run="a",
                    stage=records.GATE,
                    candidate="0000",
                    verdict="kept",
                    row=candidate_row(partition=partition),
                )
            ],
        )

    write("mandelbrot")
    write("phoenix")
    names = sorted(path.name for path in (tmp_path / records.GATE / "a").glob("*.jsonl"))
    assert names == ["phoenix.jsonl"]
    assert len(records.read_decisions(records.GATE, "a")) == 1


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


# --------------------------------------------------------------------------- #
# the serving order
# --------------------------------------------------------------------------- #
def _served_row(candidate: str, partition: str, head: str, score) -> dict:
    """One served release row: the three fields the order is taken on."""
    return records.decision(
        run="r",
        stage=records.RELEASE,
        candidate=candidate,
        verdict=records.RELEASED,
        row=candidate_row(partition=partition, head=head, p_ge3=score),
        picture=f"release/{candidate}.png",
    )


def test_a_run_serves_its_rows_in_score_rank_and_not_in_arrival_order() -> None:
    """The candidate id is the attempt number, and the attempt number is the
    position the plan's largest-deficit sequence happened to put a cell in."""
    weak = _served_row("0001", "mandelbrot", "smooth_render", 0.10)
    strong = _served_row("0007", "mandelbrot", "smooth_render", 0.90)
    middle = _served_row("0004", "mandelbrot", "smooth_render", 0.50)

    assert [row["candidate"] for row in records.served([weak, strong, middle])] == [
        "0007",
        "0004",
        "0001",
    ]


def test_the_two_judges_are_never_compared_in_one_sort() -> None:
    """A score is a probability on one head's scale. Ranked on its own scale the
    strange row leads its partition; sorted against the smooth head's number it
    would come last on the page."""
    smooth = _served_row("0001", "mandelbrot", "smooth_render", 0.98)
    strange = _served_row("0002", "mandelbrot", "strange_render", 0.71)
    quiet = _served_row("0003", "mandelbrot", "smooth_render", 0.80)

    order = [row["candidate"] for row in records.served([quiet, strange, smooth])]
    assert order[:2] == ["0001", "0002"], "each head's best sits at rank 0"
    assert order[2] == "0003"


def test_every_prefix_of_the_served_set_covers_the_partitions_evenly() -> None:
    """The near-miss section is a prefix of this order, so a partition-major sort
    would have handed the whole section to whichever partition sorts first."""
    rows = [
        _served_row("0001", "mandelbrot", "smooth_render", 0.90),
        _served_row("0002", "mandelbrot", "smooth_render", 0.80),
        _served_row("0003", "mandelbrot", "smooth_render", 0.70),
        _served_row("0004", "phoenix", "smooth_render", 0.60),
        _served_row("0005", "phoenix", "smooth_render", 0.50),
    ]
    order = [(row["location"]["partition"], row["candidate"]) for row in records.served(rows)]
    assert order[:2] == [("mandelbrot", "0001"), ("phoenix", "0004")]
    assert order[2:4] == [("mandelbrot", "0002"), ("phoenix", "0005")]
    assert order[4] == ("mandelbrot", "0003")


def test_a_partition_is_served_in_the_canonical_report_order() -> None:
    """Two rows of one rank are broken by the registry's order, not by the name."""
    julia = _served_row("0001", "julia:mandelbrot", "smooth_render", 0.99)
    plane = _served_row("0002", "mandelbrot", "smooth_render", 0.10)
    assert [row["candidate"] for row in records.served([julia, plane])] == ["0002", "0001"]


def test_a_row_with_no_score_sorts_last_inside_its_own_pool_and_is_not_a_zero() -> None:
    """A failed render has a reason instead of a number, and ranking it against a
    wallpaper is the comparison the record exists to prevent."""
    scored = _served_row("0001", "mandelbrot", "smooth_render", 0.01)
    unscored = _served_row("0002", "mandelbrot", "smooth_render", None)
    assert [row["candidate"] for row in records.score_rank([unscored, scored])] == ["0001", "0002"]
