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
from fractal_wallpapers.discovery.walk import Limits, Walk
from fractal_wallpapers.supply import proven
from fractal_wallpapers.supply import refill as refill_module
from fractal_wallpapers.supply.partitions import CLASSIC_PHOENIX, PARAMETER_PLANES
from fractal_wallpapers.supply.refill import Refill

MANDELBROT = {"kind": "mandelbrot"}
MULTIBROT3 = {"kind": "multibrot", "degree": 3}
JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}


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
    assert once["record"]["partitions"] == {
        "mandelbrot": 2,
        "multibrot3": 1,
        "multibrot4": 0,
        "multibrot5": 0,
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


def test_the_dynamical_families_are_not_this_channels_job() -> None:
    """They have screened `c`-pools; the planes are the side with no sampler."""
    rows = corpus(label(JULIA, 4, "0.1"), label(MANDELBROT, 4, "0.2"))
    record = proven.derive(rows=rows)["record"]
    assert record["rows"] == 1
    assert set(record["partitions"]) == set(PARAMETER_PLANES)


def test_a_derived_row_is_a_seed_file_row() -> None:
    """So an emitted set can be passed straight back as `--seeds`, and so the
    refill's existing plane branch can draw it without a second shape."""
    from fractal_wallpapers.discovery import pools

    row = proven.derive(rows=corpus(label(MANDELBROT, 4, "0.1")))["rows"][0]
    assert row["schema"] == proven.SCHEMA
    assert row["provenance"]["channel"] == proven.CHANNEL
    assert row["id"].startswith("proven-")
    assert pools.read_seed_file  # the reader this shape is for
    assert set(row) == {"schema", "id", "family", "viewport", "provenance"}


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
        external={CLASSIC_PHOENIX},
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
        external={CLASSIC_PHOENIX},
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
