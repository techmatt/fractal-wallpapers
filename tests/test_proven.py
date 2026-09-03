"""The proven channel: roots at places a human already scored a keeper.

The channel is a *query over the label store*, not a file, so the two things that
have to be true of it are exactly the two a file gets for free and a query does
not: the same store derives the same set, and a store that gains a keeper gains a
root without anything being refreshed. The rest of this file is the third thing —
that a harvest can reach the channel by name.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery import pools
from fractal_wallpapers.discovery.walk import Limits, Walk
from fractal_wallpapers.supply import proven
from fractal_wallpapers.supply import refill as refill_module
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    CLASSIC_PHOENIX,
    PARAMETER_PLANES,
)
from fractal_wallpapers.supply.refill import Refill

MANDELBROT = {"kind": "mandelbrot"}
MULTIBROT3 = {"kind": "multibrot", "degree": 3}
JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
PHOENIX = {"kind": "phoenix", "c": ["0.4", "0.1"], "p": ["-0.3", "0.0"], "z_prev": ["0.0", "0.0"]}
#: The pinned Ushiki point, written the way a record that names nothing is read.
CLASSIC = {"kind": "phoenix"}


def view(re: str, im: str = "0.2", width: str = "0.001") -> dict:
    return {"center_re": re, "center_im": im, "width": width}


def label(family: dict, score: int, re: str, batch: str = "a_batch", **extra) -> dict:
    """One resolved label row, the shape the store's reader hands back."""
    return {
        "schema": 1,
        "batch": batch,
        "origin": "human",
        "score": score,
        "family": family,
        "viewport": view(re),
        **extra,
    }


def corpus(*rows: dict) -> list[dict]:
    return list(rows)


# --------------------------------------------------------------------------- #
# the deriver
# --------------------------------------------------------------------------- #


def test_the_same_store_derives_the_same_bytes_whatever_order_it_is_read_in() -> None:
    """Deterministic for a fixed store, and not only per process: the order is a
    digest of the location, so it cannot depend on the reader's order or on a
    per-process hash seed."""
    rows = corpus(
        label(MANDELBROT, 3, "0.1"),
        label(MANDELBROT, 4, "0.2"),
        label(MULTIBROT3, 3, "0.3"),
    )
    once = proven.derive(rows=rows)
    again = proven.derive(rows=list(reversed(rows)))
    assert proven.render(once["rows"]) == proven.render(again["rows"])
    assert once["record"]["rows"] == 3
    assert once["record"]["partitions"] == dict.fromkeys(proven.SERVED, 0) | {
        "mandelbrot": 2,
        "multibrot3": 1,
    }


def test_the_best_tier_is_handed_over_first() -> None:
    """The refill's cursor takes the front of the list, so the order decides which
    proven places a short run actually reaches."""
    rows = corpus(*(label(MANDELBROT, 3, f"0.{step}") for step in range(1, 6)))
    rows.append(label(MANDELBROT, 4, "0.9"))
    derived = proven.derive(rows=rows)["rows"]
    assert [row["provenance"]["tier"] for row in derived] == [4, 3, 3, 3, 3, 3]
    assert derived[0]["viewport"]["center_re"] == "0.9"


def test_a_new_keeper_lands_in_the_queue_without_moving_what_is_ahead_of_it() -> None:
    """The point of ordering on a digest rather than on a seeded shuffle: a run
    resumed after a labeling session finds the roots it has not spent still
    ahead of it, rather than a queue re-dealt from the top."""
    before = corpus(*(label(MANDELBROT, 3, f"0.{step}") for step in range(1, 9)))
    after = [*before, label(MANDELBROT, 3, "0.42", batch="a_later_batch")]

    first = proven.derive(rows=before)["rows"]
    second = proven.derive(rows=after)["rows"]
    assert len(second) == len(first) + 1

    fresh = [row for row in second if row["id"] not in {row["id"] for row in first}]
    assert len(fresh) == 1
    assert fresh[0]["provenance"]["batch"] == "a_later_batch"
    # Everything else keeps both its id and its place relative to the others.
    assert [row["id"] for row in second if row != fresh[0]] == [row["id"] for row in first]


def test_the_tier_floor_is_the_currencys_bottom_class_and_is_a_parameter() -> None:
    rows = corpus(
        label(MANDELBROT, 1, "0.1"),
        label(MANDELBROT, 2, "0.2"),
        label(MANDELBROT, 3, "0.3"),
        label(MANDELBROT, 4, "0.4"),
    )
    assert proven.TIER_FLOOR == 3, "the lowest class the currency's weight table pays for"
    assert proven.derive(rows=rows)["record"]["rows"] == 2
    assert proven.derive(rows=rows, tier_floor=4)["record"]["rows"] == 1
    assert proven.derive(rows=rows, tier_floor=1)["record"]["rows"] == 4


def test_a_rule_label_is_not_a_proven_root() -> None:
    """The channel's whole claim is that a person looked at the place. A stated
    rule is a different kind of row and says so in its origin."""
    rows = corpus(
        label(MANDELBROT, 4, "0.1", origin="rule:interior_gt30_v1"),
        label(MANDELBROT, 4, "0.2"),
    )
    derived = proven.derive(rows=rows)["rows"]
    assert [row["viewport"]["center_re"] for row in derived] == ["0.2"]


def test_every_registered_partition_is_served_including_the_pinned_phoenix() -> None:
    """The planes are served because they have no sampler; the dynamical families
    because theirs cannot express a frame; `phoenix:classic` because one pinned
    point has exactly one fresh root in existence, so a labelled place is most of
    what it can be handed. It was excluded until 2026-09-02, which left its q3+
    labels the only ones in the store that became no roots."""
    rows = corpus(
        label(JULIA, 4, "0.1"),
        label(PHOENIX, 4, "0.2"),
        label(CLASSIC, 4, "0.3"),
        label(MANDELBROT, 4, "0.4"),
    )
    record = proven.derive(rows=rows)["record"]
    assert record["rows"] == 4
    assert set(record["partitions"]) == set(proven.SERVED) == set(ALL_PARTITIONS)
    assert record["partitions"][CLASSIC_PHOENIX] == 1
    assert record["partitions"]["julia:mandelbrot"] == 1
    assert record["partitions"]["phoenix"] == 1


def test_a_derived_row_is_a_seed_file_row() -> None:
    """So an emitted set can be passed straight back as `--seeds`, and so the
    refill's existing row branch can draw it without a second shape."""
    row = proven.derive(rows=corpus(label(MANDELBROT, 4, "0.1")))["rows"][0]
    assert row["schema"] == proven.SCHEMA
    assert row["provenance"]["channel"] == proven.CHANNEL
    assert row["id"].startswith("proven-")
    assert pools.read_seed_file  # the reader this shape is for
    assert set(row) == {"schema", "id", "family", "viewport", "provenance"}


# --------------------------------------------------------------------------- #
# the three stores
# --------------------------------------------------------------------------- #


def finished(family: dict, score: int, re: str, head: str = "smooth_render", **extra) -> tuple:
    """One resolved finished-render row, as `finished_verdicts` hands it over."""
    return head, label(family, score, re, **extra)


def test_a_finished_render_keeper_is_a_root_and_says_which_store_proved_it() -> None:
    """Matt's ruling, 2026-09-03: a place where a finished render was labelled q3+
    is a proven neighbourhood. It is served exactly as a location keeper is, and
    the only thing that separates the two on the row is `provenance.store`."""
    derived = proven.derive(rows=[], finished_rows=[finished(MANDELBROT, 3, "0.1")])
    assert derived["record"]["rows"] == 1
    root = derived["rows"][0]
    assert root["provenance"]["channel"] == proven.CHANNEL
    assert root["provenance"]["store"] == "smooth_render"
    assert root["viewport"] == view("0.1"), "at the place's own viewport"
    assert derived["record"]["stores"] == {
        "location": 0,
        "smooth_render": 1,
        "strange_render": 0,
    }


def test_the_tier_floor_is_the_same_floor_in_a_finished_store() -> None:
    """The floor is the currency's bottom class and not a per-store cut, so a q2
    picture buys no root however it was collected."""
    below = proven.derive(
        rows=[], finished_rows=[finished(MANDELBROT, 2, "0.1", head="strange_render")]
    )
    assert below["record"]["rows"] == 0
    above = proven.derive(
        rows=[], finished_rows=[finished(MANDELBROT, 3, "0.1", head="strange_render")]
    )
    assert above["record"]["rows"] == 1


def test_a_place_both_stores_hold_is_one_root_credited_to_the_location_store() -> None:
    """The dedup is on the PLACE. A location verdict is about the place itself and
    a finished-render verdict is about a picture standing on it, so the location
    store is credited where both hold one — and a place holding several judged
    pictures still yields one root."""
    derived = proven.derive(
        rows=corpus(label(MANDELBROT, 3, "0.1")),
        finished_rows=[
            finished(MANDELBROT, 4, "0.1"),
            finished(MANDELBROT, 4, "0.1", head="strange_render"),
            finished(MANDELBROT, 4, "0.2"),
        ],
    )
    assert derived["record"]["rows"] == 2
    stored = {row["viewport"]["center_re"]: row["provenance"] for row in derived["rows"]}
    assert stored["0.1"]["store"] == "location"
    assert stored["0.1"]["tier"] == 3, "the location row wins the place, tier and all"
    assert stored["0.2"]["store"] == "smooth_render"
    assert derived["record"]["stores"] == {
        "location": 1,
        "smooth_render": 1,
        "strange_render": 0,
    }


def test_a_checkout_with_no_finished_verdicts_derives_what_it_always_did() -> None:
    """The union only ever adds places. With the finished side empty the set is
    the location store's, row for row and byte for byte."""
    rows = corpus(label(MANDELBROT, 4, "0.1"), label(MULTIBROT3, 3, "0.3"))
    alone = proven.derive(rows=rows)
    unioned = proven.derive(rows=rows, finished_rows=[])
    assert proven.render(alone["rows"]) == proven.render(unioned["rows"])
    assert alone["record"]["rows"] == unioned["record"]["rows"] == 2
    assert alone["record"]["stores"]["location"] == 2


def test_naming_either_corpus_reads_neither_store_off_disk() -> None:
    """Injection is all-or-nothing: a test that hands over a corpus is asking
    about that corpus, and a derive that unioned it with the checkout's own stores
    would answer about something else."""
    only_finished = proven.derive(finished_rows=[finished(MANDELBROT, 4, "0.1")])
    assert only_finished["record"]["stores"]["location"] == 0
    only_location = proven.derive(rows=corpus(label(MANDELBROT, 4, "0.1")))
    assert only_location["record"]["stores"]["smooth_render"] == 0


# --------------------------------------------------------------------------- #
# the interleave, and the comparison
# --------------------------------------------------------------------------- #


def test_the_pool_is_interleaved_rather_than_displaced() -> None:
    """A channel fed by this project's own past output cannot open new ground, so
    a queue that spent itself on proven roots first would reach new ground only
    after it ran out."""
    mixed = proven.interleave(["p0", "p1", "p2", "p3"], ["f0", "f1"], ratio=2)
    assert mixed == ["p0", "p1", "f0", "p2", "p3", "f1"]
    assert proven.interleave(["p0"], ["f0", "f1", "f2"]) == ["p0", "f0", "f1", "f2"]
    assert proven.interleave([], ["f0"]) == ["f0"]
    assert proven.interleave(["p0", "p1"], []) == ["p0", "p1"]


def test_a_comparison_counts_growth_one_way_and_refuses_to_shrug_at_the_other(
    tmp_path,
) -> None:
    """Growth is the point; a location the file had and a derivation does not
    means a verdict moved, and that is a thing to explain."""
    rows = corpus(label(MANDELBROT, 4, "0.1"), label(MANDELBROT, 3, "0.2"))
    path = tmp_path / "seeds.jsonl"
    proven.write(proven.derive(rows=rows[:1])["rows"], path)

    grown = proven.compare(proven.derive(rows=rows)["rows"], path)
    assert (grown["gained"], grown["lost"]) == (1, 0)
    assert grown["gained_tiers"] == {3: 1}

    lowered = proven.compare(proven.derive(rows=rows, tier_floor=4)["rows"][1:], path)
    assert lowered["lost"] == 1
    assert lowered["lost_sample"] == [json.loads(path.read_text(encoding="utf-8"))["id"]]

    assert proven.compare([], tmp_path / "absent.jsonl")["compared"] is False


# --------------------------------------------------------------------------- #
# the channel, inside a refill
# --------------------------------------------------------------------------- #


def channel(rows=None, **kwargs) -> proven.ProvenChannel:
    if rows is None:
        rows = corpus(label(MANDELBROT, 4, "-0.75"), label(MANDELBROT, 3, "-0.74"))
    return proven.build(rows=rows, **kwargs)


def refill_of(tmp_path, live, monkeypatch, **kwargs) -> tuple[Walk, Refill]:
    """A refill over the parameter planes alone, with no pool behind it — so what
    a draw hands over is this channel's and nothing else's.

    The tracked plane pool is the default channel on a checkout that has derived
    it, so a test that wants the proven channel alone has to say so.
    """
    monkeypatch.setattr(refill_module, "_tracked_plane_pool", lambda: None)
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    return walk, Refill(
        walk,
        low_water=2,
        per_draw=2,
        partitions=list(PARAMETER_PLANES),
        seeds=None,
        proven=live,
        **kwargs,
    )


def test_a_plane_with_proven_roots_has_a_channel_without_any_seed_file(
    tmp_path, monkeypatch
) -> None:
    walk, refill = refill_of(tmp_path, channel(), monkeypatch)
    queues = dict.fromkeys(PARAMETER_PLANES, 0)

    assert refill.has_channel("mandelbrot") is True
    assert refill.remaining("mandelbrot") == 2
    assert refill.starved(queues, batch=0) == ["mandelbrot"]
    deferred = refill.deferred(queues)
    assert "mandelbrot" not in deferred
    assert "proven" in deferred["multibrot3"]["reason"], "the plane with no roots says so"


def test_a_draw_roots_the_walk_at_a_labelled_place_and_says_which_channel(
    tmp_path, monkeypatch
) -> None:
    walk, refill = refill_of(tmp_path, channel(), monkeypatch)
    outcome = refill.run(dict.fromkeys(PARAMETER_PLANES, 0), batch=0, loop_seconds=1.0)

    assert outcome == {"refilled": ["mandelbrot"], "roots": 2}
    roots = [row for row in ledger_module.read(walk.ledger.path) if row["kind"] == "root"]
    assert {row["provenance"]["channel"] for row in roots} == {proven.CHANNEL}
    assert {row["source"] for row in roots} == {"seed_file"}, (
        "one source for the whole plane channel: the expansion grace turns on it"
    )
    # The frames are the labelled ones, not a home view.
    assert {node["center_re"] for node in walk.frontier} == {"-0.75", "-0.74"}
    # Best tier first, through the cursor.
    assert roots[0]["provenance"]["seed_id"] == channel().seeds("mandelbrot")[0]["id"]


def test_the_channel_grows_when_a_qualifying_label_lands(tmp_path, monkeypatch) -> None:
    """The reason it is a query and not a file: nothing has to be refreshed."""
    rows = corpus(label(MANDELBROT, 4, "-0.75"))
    _walk, before = refill_of(tmp_path / "before", channel(rows), monkeypatch)
    assert before.remaining("mandelbrot") == 1

    rows.append(label(MANDELBROT, 3, "-0.74", batch="a_later_batch"))
    rows.append(label(MANDELBROT, 2, "-0.73", batch="a_later_batch"))
    _walk, after = refill_of(tmp_path / "after", channel(rows), monkeypatch)
    assert after.remaining("mandelbrot") == 2, "the keeper became a root; the class 2 did not"


def test_a_seed_file_and_the_proven_channel_share_one_queue(tmp_path) -> None:
    """Both are the plane channel, so both move one cursor: two cursors served in
    whatever order a queue drains would decide the mix by accident."""
    seeds = tmp_path / "seeds.jsonl"
    seeds.write_text(
        "".join(
            json.dumps(
                {
                    "schema": 1,
                    "id": f"fresh-{step}",
                    "family": MANDELBROT,
                    "viewport": view(f"0.{step}"),
                    "provenance": {"channel": "nucleus_grid"},
                }
            )
            + "\n"
            for step in range(3)
        ),
        encoding="utf-8",
    )
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    refill = Refill(
        walk,
        low_water=2,
        per_draw=9,
        partitions=list(PARAMETER_PLANES),
        seeds=seeds,
        proven=channel(),
    )
    refill.run(dict.fromkeys(PARAMETER_PLANES, 0), batch=0, loop_seconds=1.0)
    roots = [row for row in ledger_module.read(walk.ledger.path) if row["kind"] == "root"]
    assert [row["provenance"]["channel"] for row in roots] == [
        proven.CHANNEL,
        proven.CHANNEL,
        "nucleus_grid",
        "nucleus_grid",
        "nucleus_grid",
    ], "two proven per pool root, and the pool is not crowded out"


def test_a_proven_dynamical_root_starts_at_the_labelled_frame_not_the_home_view(
    tmp_path, monkeypatch
) -> None:
    """The whole of what this channel is worth on a dynamical partition. A
    `c`-pool row is a *parameter*, so every root it hands over comes up at the
    home view — the whole plane at width 3.0 — and the walk descends from there.
    A label row carries the frame the human was looking at."""
    # The tracked `c`-pool out of the way, so what a draw hands over is this
    # channel's and the queue is not two entries deep in parameters first.
    monkeypatch.setattr(pools, "julia_pool", lambda *a, **k: [])
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    refill = Refill(
        walk,
        low_water=2,
        per_draw=2,
        partitions=["julia:mandelbrot"],
        seeds=None,
        proven=channel(corpus(label(JULIA, 4, "-0.4"))),
    )
    assert refill.has_channel("julia:mandelbrot") is True
    assert refill.run({"julia:mandelbrot": 0}, batch=0, loop_seconds=1.0)["roots"] == 1

    root = next(row for row in ledger_module.read(walk.ledger.path) if row["kind"] == "root")
    assert root["family"] == JULIA
    assert root["viewport"] == {"center_re": "-0.4", "center_im": "0.2", "width": "0.001"}
    assert root["provenance"]["channel"] == proven.CHANNEL
    assert root["source"] == "seed_file", "one source for every row-shaped entry"
    # And no expansion grace: the source is half of that predicate and the family
    # is the other half, which is `None` for a dynamical one.
    assert root["plane_root"] is False


def test_one_queue_holds_a_parameter_and_a_place_and_tells_them_apart_by_shape(
    tmp_path,
) -> None:
    """The mismatch this channel's reach created, resolved once. Both entries
    reach the same partition through the same cursor: the pool's typed seed,
    which has no frame in it, and the row, which is a whole location."""
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    refill = Refill(walk, partitions=["julia:mandelbrot"], seeds=None, proven=None)

    seed = pools.JuliaSeed(id="c0007", c=("-0.75", "0.11"), channel="near_boundary")
    parameter = refill._root_of("julia:mandelbrot", seed, 0)
    assert parameter["viewport"] is None, "a parameter comes up at the family's home view"
    assert parameter["source"] == "julia_c_pool"
    assert parameter["family"] == {"kind": "julia", "degree": 2, "c": ["-0.75", "0.11"]}

    row = proven.derive(rows=corpus(label(JULIA, 4, "-0.4")))["rows"][0]
    place = refill._root_of("julia:mandelbrot", row, 1)
    assert place["viewport"] == row["viewport"], "a location comes up at its own frame"
    assert place["source"] == "seed_file"
    assert place["provenance"]["file"] is None, "derived, not out of a file"

    with pytest.raises(TypeError, match="julia:mandelbrot"):
        refill._root_of("julia:mandelbrot", object(), 2)


def test_the_pinned_classic_phoenix_draws_one_fresh_root_and_its_proven_places(
    tmp_path,
) -> None:
    """Its queue is the one thing a pinned plane can offer — the home view — with
    every labelled place interleaved through it. It was refused a channel outright
    until 2026-09-02, first and unconditionally, so its labels became no roots and
    no walk ever rendered a frame of it."""
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    live = proven.build(rows=corpus(label(CLASSIC, 4, "0.3")), partitions=[CLASSIC_PHOENIX])
    assert live.partitions == (CLASSIC_PHOENIX,), "served, so it has a queue"

    refill = Refill(
        walk,
        low_water=2,
        partitions=[CLASSIC_PHOENIX, "phoenix"],
        seeds=None,
        proven=proven.build(rows=corpus(label(CLASSIC, 4, "0.3"), label(PHOENIX, 4, "0.4"))),
    )
    assert refill.has_channel(CLASSIC_PHOENIX) is True
    assert refill.has_channel("phoenix") is True
    assert refill.starved(dict.fromkeys([CLASSIC_PHOENIX, "phoenix"], 0), batch=0) == [
        CLASSIC_PHOENIX,
        "phoenix",
    ]

    queue = refill._pool(CLASSIC_PHOENIX)
    assert len(queue) == 2, "the home view, and the one labelled place"
    roots = {
        root["source"]: root
        for root in (refill._root_of(CLASSIC_PHOENIX, entry, at) for at, entry in enumerate(queue))
    }
    fresh, proven_root = roots["classic_phoenix_point"], roots["seed_file"]
    assert fresh["viewport"] is None, "a fresh root comes up at the home view"
    assert fresh["provenance"]["file"] is None, "synthesized, not read out of a pool file"
    assert proven_root["provenance"]["channel"] == proven.CHANNEL
    assert proven_root["viewport"] is not None, "a labelled place carries its own frame"


def test_the_census_says_how_much_of_a_queue_came_from_the_label_store(
    tmp_path, monkeypatch
) -> None:
    """A dynamical queue out of `c` and a dynamical queue out of labelled places
    exhaust in different ways, and "entries left" alone cannot tell them apart."""
    monkeypatch.setattr(pools, "julia_pool", lambda *a, **k: [])
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    refill = Refill(
        walk,
        low_water=2,
        partitions=["julia:mandelbrot"],
        seeds=None,
        proven=channel(corpus(label(JULIA, 4, "-0.4"), label(JULIA, 3, "-0.41"))),
    )
    state = refill.pool_state()["julia:mandelbrot"]
    assert (state["pool"], state["proven"], state["reason"]) == (2, 2, None)
    assert "2 of them proven roots" in refill.pool_lines()[0]


def test_the_summary_says_the_channel_was_wired_and_at_what_floor(tmp_path, monkeypatch) -> None:
    _walk, refill = refill_of(tmp_path, channel(), monkeypatch)
    summary = refill.summary()["proven"]
    assert summary["channel"] == proven.CHANNEL
    assert summary["tier_floor"] == proven.TIER_FLOOR
    assert summary["ratio"] == proven.RATIO
    assert summary["seeds"] == {"mandelbrot": 2}

    _walk, without = refill_of(tmp_path / "off", None, monkeypatch)
    assert without.summary()["proven"] is None, "off is a state, and it is stated"


# --------------------------------------------------------------------------- #
# by name, from the command line
# --------------------------------------------------------------------------- #


def test_a_harvest_reaches_the_channel_by_name() -> None:
    """The whole point of registering it: `--root-channel proven` and the
    run holds the channel, with no seed file built by hand anywhere."""
    from fractal_wallpapers import cli

    parse = cli.build_parser().parse_args
    assert parse(["harvest"]).root_channels is None
    assert parse(["harvest", "--root-channel", "proven"]).root_channels == ["proven"]

    off = cli.build_proven_channel(parse(["harvest"]), ["mandelbrot"])
    assert off is None, "off by default: adopting a self-fed channel is a run's decision"

    live = cli.build_proven_channel(parse(["harvest", "--root-channel", "proven"]), ["mandelbrot"])
    assert live.partitions == ("mandelbrot",), "the run's own partition list, met with the planes"
    assert live.summary()["tier_floor"] == proven.TIER_FLOOR
    assert live.seeds("mandelbrot"), "the tracked corpus holds mandelbrot keepers"


def test_a_channel_name_nobody_registered_is_refused_at_the_parser() -> None:
    from fractal_wallpapers import cli

    # `proven_label` is in the list because it is the name this channel shipped
    # under for one commit: a retired name has to stop being accepted, or a run
    # script that was never updated keeps working and nobody learns the new one.
    for name in ("nucleus_grid", "twins", "proven_label"):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["harvest", "--root-channel", name])


def test_the_parser_offers_exactly_the_partitions_the_channel_serves() -> None:
    """`derive` filters on the list it is handed, so a subcommand offering a
    partition the channel does not serve would print an empty seed set reading
    exactly like a full one. The two lists are the same list now."""
    from fractal_wallpapers import cli

    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["derive-proven-seeds", "--partition", "nonesuch"])
    parsed = cli.build_parser().parse_args(
        ["derive-proven-seeds", "--partition", CLASSIC_PHOENIX, "--partition", "julia:mandelbrot"]
    )
    assert parsed.partition == [CLASSIC_PHOENIX, "julia:mandelbrot"]


@pytest.mark.slow
def test_the_subcommand_emits_the_set_and_compares_it(tmp_path, capsys) -> None:
    from fractal_wallpapers import cli

    out = tmp_path / "emitted.jsonl"
    code = cli.main(
        ["derive-proven-seeds", "--partition", "mandelbrot", "--write", "--out", str(out)]
    )
    assert code == 0
    emitted = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert emitted, "the tracked corpus holds mandelbrot keepers"
    assert {row["provenance"]["channel"] for row in emitted} == {proven.CHANNEL}
    capsys.readouterr()

    assert (
        cli.main(["derive-proven-seeds", "--partition", "mandelbrot", "--against", str(out)]) == 0
    )
    assert (
        cli.main(
            [
                "derive-proven-seeds",
                "--partition",
                "mandelbrot",
                "--tier-floor",
                "4",
                "--against",
                str(out),
            ]
        )
        == 1
    ), "raising the floor loses locations the file had, and that is not a shrug"
