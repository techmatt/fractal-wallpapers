"""Picture retention: what is kept, what the aggregates hold, and what is never dropped.

Arithmetic over rows, like [`test_mine`] and [`test_depth`]. Nothing renders and
nothing is deleted — this module has no delete in it at all, which is the first
property pinned here.

The claims worth pinning hardest are the ones a wrong decision would hide. **A
row is never dropped**, because recipe-key dedup is the ledger's reason for
existing and a pass that could not tell it had already made a picture would
re-render it. **The ranking is within the (location, mode) pair** and never
against an absolute probability, because CORN's scale moves under every retrain
and the per-mode crossovers already span 0.367 to 0.950. And **the reservoir is
a hash and not a draw**, so the same tenth of a percent is kept in every process
that asks.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import retention

VIEWPORT = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}
PALETTE = {
    "gamma": 1.0,
    "cycles": 1.0,
    "phase": 0.0,
    "reverse": False,
    "mirror": False,
    "transfer": {"kind": "value"},
    "rolloff": {"kind": "none"},
}


def a_row(key, place="p", mode="smooth", colormap="viridis", cells=(), picture="a.jpg"):
    """One ledger row, thinned to the members a retention decision reads."""
    return {
        "key": key,
        "location": {"key": place},
        "recipe": {
            "family": {"kind": "mandelbrot"},
            "viewport": VIEWPORT,
            "mode": mode,
            "mode_params": {},
            "curve": "linear",
            "colormap": colormap,
            "palette": PALETTE,
        },
        "colour": {"cells": list(cells), "families": []},
        "picture": picture,
    }


# --------------------------------------------------------------------------- #
# The rule.
# --------------------------------------------------------------------------- #
def test_the_top_n_of_a_pair_are_kept_and_ranked_inside_the_pair():
    rows = [a_row(f"k{at}") for at in range(8)]
    scores = {f"k{at}": at / 10 for at in range(8)}
    out = retention.decide(rows, scores, labeled=set(), keep=3)
    ranked = [key for key, reason in out.items() if reason == retention.RANKED]
    assert sorted(ranked) == ["k5", "k6", "k7"], "the three highest of the pair"


def test_the_ranking_never_crosses_a_mode_or_a_location():
    """A pair's fifth-best is kept even where another pair's sixth-best scores
    higher. An absolute cut would take the whole of one mode and none of another
    — the per-mode crossovers span 0.367 to 0.950 and one number cannot be the
    bar for all of them."""
    rows = [a_row(f"a{at}", mode="smooth") for at in range(3)]
    rows += [a_row(f"b{at}", mode="stripe") for at in range(3)]
    scores = {f"a{at}": 0.9 for at in range(3)} | {f"b{at}": 0.01 for at in range(3)}
    out = retention.decide(rows, scores, labeled=set(), keep=2)
    assert sum(1 for key in ("a0", "a1", "a2") if out[key] == retention.RANKED) == 2
    assert sum(1 for key in ("b0", "b1", "b2") if out[key] == retention.RANKED) == 2, (
        "the weak mode keeps its own best two, at a hundredth of the strong mode's score"
    )


def test_a_row_with_no_score_ranks_last_rather_than_being_thrown_out():
    """Nothing has an opinion about it, which is not the same as something
    thinking little of it."""
    rows = [a_row("scored"), a_row("silent")]
    out = retention.decide(rows, {"scored": 0.0}, labeled=set(), keep=1)
    assert out["scored"] == retention.RANKED
    assert out["silent"] != retention.RANKED


def test_a_labeled_row_is_kept_however_far_down_the_ranking_it_is():
    rows = [a_row(f"k{at}") for at in range(20)]
    scores = {f"k{at}": 1.0 - at / 100 for at in range(20)}
    labeled = {retention.render_key_of(rows[19])}
    out = retention.decide(rows, scores, labeled=labeled, keep=2)
    assert out["k19"] == retention.LABELED, "last of twenty, and instrument"


def test_the_reservoir_is_a_hash_of_the_key_and_not_a_draw():
    """The same tenth of a percent in every process that asks. `hash()` is
    salted per process and would keep a different set on every run."""
    assert retention.in_reservoir("some-key", one_in=1)
    picked = {key for key in (f"k{at:06d}" for at in range(4000)) if retention.in_reservoir(key)}
    again = {key for key in (f"k{at:06d}" for at in range(4000)) if retention.in_reservoir(key)}
    assert picked == again
    assert 5 <= len(picked) <= 45, f"1 in 200 of 4,000 is about 20; got {len(picked)}"


def test_the_reservoir_only_catches_what_the_ranking_dropped():
    rows = [a_row(f"k{at}") for at in range(40)]
    scores = {f"k{at}": at for at in range(40)}
    out = retention.decide(rows, scores, labeled=set(), keep=5, one_in=1)
    kept_by_rank = [key for key, reason in out.items() if reason == retention.RANKED]
    assert len(kept_by_rank) == 5
    assert all(
        reason == retention.RESERVOIR for key, reason in out.items() if key not in kept_by_rank
    )


def test_every_row_gets_exactly_one_reason_and_all_of_them_are_named():
    rows = [a_row(f"k{at}") for at in range(30)]
    out = retention.decide(rows, {f"k{at}": at for at in range(30)}, labeled=set(), keep=4)
    assert set(out) == {f"k{at}" for at in range(30)}
    assert set(out.values()) <= set(retention.REASONS)
    assert retention.kept(retention.RANKED)
    assert retention.kept(retention.LABELED)
    assert retention.kept(retention.RESERVOIR)
    assert not retention.kept(retention.DROPPED)


def test_the_module_that_decides_what_to_delete_cannot_delete():
    """The policy is a decision and applying it is not this module's job. A
    delete in here is how a report becomes a prune by accident."""
    import inspect

    source = inspect.getsource(retention)
    for forbidden in ("unlink(", "rmtree", "os.remove", "shutil.move", "rename("):
        assert forbidden not in source, forbidden


# --------------------------------------------------------------------------- #
# The three aggregates.
# --------------------------------------------------------------------------- #
def test_the_place_mode_count_carries_the_pool_it_is_a_cursor_into():
    """The count says how much of a seeded permutation has been spent. Change
    the library and the same count names different maps."""
    rows = [a_row("k1"), a_row("k2"), a_row("k3", mode="stripe")]
    out = retention.by_place_mode(rows, stamp=retention.pool_stamp(["a", "b"]))
    assert out[("p", "smooth")]["attempts"] == 2
    assert out[("p", "stripe")]["attempts"] == 1
    assert out[("p", "smooth")]["pool_stamp"] == retention.pool_stamp(["a", "b"])
    assert retention.pool_stamp(["a", "b"]) != retention.pool_stamp(["a", "c"])
    assert retention.pool_stamp(["a", "b"]) != retention.pool_stamp(["b", "a"]), (
        "order is part of a permutation's identity"
    )


def test_the_map_mode_count_keeps_colormap_identity_off_the_discards():
    """The one signal a discard genuinely destroys. Drop the colormap with the
    picture and 'which palettes never work anywhere' stops being askable."""
    rows = [
        a_row("k1", colormap="viridis"),
        a_row("k2", colormap="viridis"),
        a_row("k3", colormap="magma"),
    ]
    out = retention.by_map_mode(rows, {"k1": 0.9, "k2": 0.1}, bar=0.5)
    assert out[("viridis", "smooth")] == {"attempts": 2, "scored": 2, "successes": 1}
    assert out[("magma", "smooth")] == {"attempts": 1, "scored": 0, "successes": 0}, (
        "an unscored row is an attempt and not a failure"
    )


def test_the_place_cell_count_is_read_off_the_stored_colour_and_not_off_a_table():
    """What a place ACTUALLY produced. The carrier table is a prior about a map."""
    rows = [
        a_row("k1", cells=["dark_vivid_green"]),
        a_row("k2", cells=["dark_vivid_green", "dark_muted_rose"]),
        a_row("k3", cells=[]),
    ]
    out = retention.by_place_cell(rows)
    assert out[("p", "dark_vivid_green")] == {"attempts": 3, "dominant": 2}
    assert out[("p", "dark_muted_rose")] == {"attempts": 3, "dominant": 1}
    assert ("p", "dark_vivid_blue") not in out, (
        "a colour a place has never delivered is the ABSENCE of a row, which is what "
        "a targeted mine tests for"
    )


def test_the_aggregates_are_bounded_by_their_key_spaces_and_not_by_the_attempts():
    """The whole point. Ten times the attempts at the same places, in the same
    modes, through the same maps is the same size of aggregate."""
    one = [a_row(f"k{at}", cells=["dark_vivid_green"]) for at in range(20)]
    ten = [a_row(f"k{at}", cells=["dark_vivid_green"]) for at in range(200)]
    small = retention.aggregates(one, {}, "stamp")
    large = retention.aggregates(ten, {}, "stamp")
    for name in ("place_mode", "map_mode", "place_cell"):
        assert small[name]["pairs"] == large[name]["pairs"], name
    assert large["attempts"] == 200


# --------------------------------------------------------------------------- #
# The report.
# --------------------------------------------------------------------------- #
def test_the_report_says_it_applied_nothing(tmp_path):
    rows = [a_row(f"k{at}", picture=None) for at in range(12)]
    out = retention.prune_report(
        rows, {f"k{at}": at for at in range(12)}, labeled=set(), keep=3, log=lambda *_: None
    )
    assert out["applied"] is False
    assert out["policy"]["rows_dropped"].startswith("never")
    assert out["rows"] == 12
    assert out["would_keep"] + out["would_delete"] == 12
    assert out["pictures"]["row_names_none"] == 12
    assert out["bytes"]["would_delete"] == 0


def test_the_report_sizes_only_the_pictures_that_are_on_this_machine(tmp_path):
    real = tmp_path / "real.jpg"
    real.write_bytes(b"x" * 1000)
    rows = [
        a_row("keeper", picture=str(real)),
        a_row("goner", picture=str(tmp_path / "gone.jpg")),
    ]
    out = retention.prune_report(
        rows, {"keeper": 1.0, "goner": 0.0}, labeled=set(), keep=1, log=lambda *_: None
    )
    assert out["bytes"]["would_keep"] == 1000
    assert out["pictures"]["named_but_absent"] == 1


def test_the_report_breaks_the_deletion_down_by_mode():
    rows = [a_row(f"s{at}", mode="smooth", picture=None) for at in range(8)]
    rows += [a_row(f"t{at}", mode="stripe", picture=None) for at in range(4)]
    scores = {row["key"]: 0.5 for row in rows}
    out = retention.prune_report(rows, scores, labeled=set(), keep=2, log=lambda *_: None)
    assert out["by_mode"]["smooth"][retention.RANKED] == 2
    assert out["by_mode"]["stripe"][retention.RANKED] == 2
    assert sum(out["by_mode"][mode][retention.DROPPED] for mode in ("smooth", "stripe")) == 8


# --------------------------------------------------------------------------- #
# Over the real store.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_every_ledger_row_can_be_spelled_as_a_render_key_for_the_label_join(tracked_ledger):
    """A row that cannot be keyed could never be found to carry a label, and
    would be dropped as unlabeled without anything saying so.

    Whole-store on purpose — the claim is about every row, and once the reading
    is the session's the sweep itself is arithmetic. See `conftest.tracked_ledger`.
    """
    rows = tracked_ledger.rows
    unkeyable = [row["key"] for row in rows if retention.render_key_of(row) is None]
    assert unkeyable == [], f"{len(unkeyable)} of {len(rows)} rows cannot be keyed"


@pytest.mark.slow
def test_the_policy_keeps_every_human_labeled_row_on_the_real_store(tracked_ledger):
    from fractal_wallpapers.curation import candidate_ledger

    rows = tracked_ledger.rows
    scores = {
        key: float(row.get("p_ge4") or 0.0)
        for key, row in candidate_ledger.scores_by_recipe(tracked_ledger.scores).items()
    }
    labeled = retention.labeled_renders()
    out = retention.decide(rows, scores, labeled)
    missed = [
        row["key"]
        for row in rows
        if retention.render_key_of(row) in labeled and not retention.kept(out[str(row["key"])])
    ]
    assert missed == [], f"{len(missed)} labeled row(s) would lose their picture"
