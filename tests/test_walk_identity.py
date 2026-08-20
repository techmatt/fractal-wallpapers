"""Why a walk may score its own gate render, and what refuses when it may not.

The whole change these cover replaced a second render per survivor — the deploy
geometry, 58.7% of a production run's clean wall — with the picture `expand`
already wrote. That is only legitimate while four settings hold, and the failure
if one of them moves is a full ledger of scores read off a distribution the head
never saw, which looks exactly like a good ledger. So every one of the four is
pinned here in both directions: the record it writes when it holds, and the
sentence it refuses with when it does not.

Nothing here needs weights or the tile corpus. The scorers are stubs and the cap
check reads a manifest these tests write, which is what lets the refusals be
proven on a machine that could not run the thing they protect.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import identity
from fractal_wallpapers.discovery.scoring import Reading
from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
from fractal_wallpapers.models import tiles as tile_module

NODE = tile_module.NODE_REGIME

#: Three frames the walk tests already stand on, known to produce candidates
#: through the real gates, so a smoke walk here has something to score.
SEEDS = (
    ("-0.7453", "0.1127", "0.2"),
    ("0.2929", "0.0149", "0.1"),
    ("-0.748", "0.263", "0.06"),
)


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


class Judge:
    """A scorer that declares a regime and remembers what it was handed.

    The regime is the whole point: it is what makes a walk assert the identity at
    all, and what a reading stamps onto the row.
    """

    name = "judge"

    def __init__(self, value: float = 0.9, regime=NODE):
        self.value = value
        self.regime = regime
        self.offered: list = []

    def at(self, regime, directory):
        """The same judge at another geometry — the door `dual_score` asks through.

        The twin answers zero, so every decision moves and the flip count under
        test is a number the two arms genuinely disagree about rather than a
        structural zero that would pass whatever the comparison did.
        """
        twin = Judge(0.0, regime)
        twin.directory = directory
        return twin

    def score(self, candidate):
        return self.value

    def read(self, candidates, pictures=None):
        self.offered.append(None if pictures is None else [str(p) for p in pictures])
        return [
            Reading(self.value, self.value, None, (), self.regime.spelled, f"digest{index}")
            for index, _ in enumerate(candidates)
        ]

    def admits(self, candidate, score):
        return True

    def expandable(self, candidate, score):
        return True


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """A tile manifest whose recorded caps are the engine's own, for one regime.

    Written rather than read: the real one is three hundred megabytes and may be
    archived, and what the check is *about* is whether the recorded number and
    the engine's policy still agree — which a small honest manifest states as
    well as a large one.
    """
    widths = ["0.2", "0.01", "0.0004", "3.1e-06"]
    caps = engine.maxiter_for(widths) if engine_is_built() else [4000, 5000, 6000, 7000]
    path = tmp_path / "manifest.jsonl"

    def write(overrides: dict | None = None) -> None:
        overrides = overrides or {}
        rows = []
        for index, (width, cap) in enumerate(zip(widths, caps, strict=True)):
            # Two tiles per location, so the prefix reader is exercised on a
            # manifest that repeats a location the way a real one does.
            for tile in (0, 1):
                rows.append(
                    {
                        "location_id": index,
                        "tile": tile,
                        "maxiter": overrides.get(index, cap),
                        "location": {"width": width},
                    }
                )
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
        )

    write()
    monkeypatch.setattr(tile_module, "manifest_path", lambda regime=None: path)
    return write


def walk(tmp_path, scorer, corpus=None, **kwargs) -> Walk:
    kwargs.setdefault("seed", 20260820)
    kwargs.setdefault("limits", Limits(batch=3, batches=2, root_expansions=4))
    kwargs.setdefault("policy", Policy(candidates=2, node_width=NODE.tile[0]))
    return Walk(out_dir=tmp_path / "walk", scorer=scorer, **kwargs)


def rooted(run: Walk) -> Walk:
    """Every seed pushed as a root, so a smoke walk has somewhere to start."""
    for index, (centre_re, centre_im, width) in enumerate(SEEDS):
        run.add_root(
            {"kind": "mandelbrot"},
            {"center_re": centre_re, "center_im": centre_im, "width": width},
            source="test",
            provenance={"seed_id": f"s{index}"},
        )
    return run


# --------------------------------------------------------------------------- #
# The four settings, each planted red.
# --------------------------------------------------------------------------- #
@needs_engine
def test_the_identity_holds_and_the_run_records_what_it_checked(tmp_path, corpus) -> None:
    """A run that scores its own gate renders is answerable for that claim, so the
    claim travels with the ledger rather than only with the code."""
    run = walk(tmp_path, Judge())
    assert run.identity["regime"] == NODE.spelled
    assert run.identity["cyclic"] is True
    assert run.identity["node_width"] == NODE.tile[0]
    assert run.identity["caps"]["matched"] == run.identity["caps"]["locations"] == 4

    header = json.loads(run.ledger.path.read_text(encoding="utf-8").splitlines()[0])
    assert header["identity"] == run.identity, "the header carries it, not just the object"


def test_a_walk_that_draws_through_another_map_refuses(tmp_path, corpus) -> None:
    """The head reads the gate render as a tile, and a tile is drawn through the
    tile pool's floor palette."""
    with pytest.raises(identity.IdentityBroken) as refusal:
        walk(tmp_path, Judge(), colormap="magma")
    assert "magma" in str(refusal.value)
    assert "twilight_shifted" in str(refusal.value), "it names the map to use"


def test_a_non_cyclic_map_refuses_rather_than_folding(tmp_path, corpus, monkeypatch) -> None:
    """The tile path mirrors the palette of a map that does not wrap and the node
    path never mirrors, so the two would be different pictures of one place."""
    from fractal_wallpapers.models import location_view

    monkeypatch.setattr(location_view, "canonical_map", lambda: "Blues")
    monkeypatch.setattr(location_view, "cyclic_maps", lambda: {"twilight_shifted"})
    with pytest.raises(identity.IdentityBroken) as refusal:
        walk(tmp_path, Judge(), colormap="Blues")
    assert "cyclic" in str(refusal.value)


def test_a_node_width_the_head_has_no_tiles_of_refuses(tmp_path, corpus) -> None:
    """`--node-width` is a live flag, and moving it moves the gate render's frame
    out of every regime the corpus was built at."""
    with pytest.raises(identity.IdentityBroken) as refusal:
        walk(tmp_path, Judge(), policy=Policy(candidates=2, node_width=512))
    assert "512" in str(refusal.value)
    assert NODE.spelled in str(refusal.value)


@needs_engine
def test_a_cap_policy_that_moved_since_the_corpus_was_built_refuses(tmp_path, corpus) -> None:
    """The cap decides what counts as interior, so a corpus built under one policy
    and a walk drawn under another are two different pictures of every location —
    and nothing about either one looks wrong."""
    corpus({1: 12345})
    with pytest.raises(identity.IdentityBroken) as refusal:
        walk(tmp_path, Judge())
    assert "cap" in str(refusal.value)
    assert "12345" in str(refusal.value), "it names the disagreement it found"


def test_a_corpus_that_is_not_on_this_machine_refuses_rather_than_assuming(
    tmp_path, monkeypatch
) -> None:
    """An unchecked identity is not a held one. The message is an instruction: the
    two ways to get the records back, and the flag that walks without them."""
    monkeypatch.setattr(
        tile_module, "manifest_path", lambda regime=None: tmp_path / "gone" / "manifest.jsonl"
    )
    with pytest.raises(identity.IdentityBroken) as refusal:
        walk(tmp_path, Judge())
    assert "--no-scoring" in str(refusal.value)
    assert "storage restore" in str(refusal.value)


def test_a_scorer_that_declares_no_regime_asserts_nothing(tmp_path) -> None:
    """The null scorer makes no claim about what `expand` drew, so there is nothing
    to check and nothing to refuse — which is what keeps a walk runnable on a
    machine with no weights and no corpus."""
    from fractal_wallpapers.discovery.scoring import NullScorer

    run = walk(tmp_path, NullScorer())
    assert run.identity is None
    assert run.gate_flips() is None


# --------------------------------------------------------------------------- #
# What the engine actually drew.
# --------------------------------------------------------------------------- #
def test_a_batch_drawn_at_another_geometry_is_refused_on_the_engine_s_own_word(
    tmp_path, corpus
) -> None:
    """The run-start check pins the settings; this pins the outcome. The engine
    states the regime it drew at, so a frame-size change cannot make "the head
    reads the gate render" quietly false."""
    run = walk(tmp_path, Judge())
    report = {"tile": [640, 360], "field_supersample": 2, "candidates": [], "dead": []}
    with pytest.raises(identity.IdentityBroken) as refusal:
        run._record(report, {}, {"kind": "mandelbrot"})
    assert "640x360ss2" in str(refusal.value)
    assert NODE.spelled in str(refusal.value)


@needs_engine
def test_the_walk_hands_the_scorer_the_picture_the_engine_already_made(tmp_path, corpus) -> None:
    """The whole change: a survivor's score is read off the gate render, and no
    view is drawn for scoring at all."""
    judge = Judge()
    run = rooted(walk(tmp_path, judge))
    run.run()

    offered = [batch for batch in judge.offered if batch]
    assert offered, "the scorer was handed no pictures at all"
    for batch in offered:
        for picture in batch:
            assert picture.startswith(str(run.views_dir())), "not the run's own gate render"
            assert picture.endswith(".jpg")


@needs_engine
def test_a_judge_that_reads_another_geometry_is_offered_nothing(tmp_path, corpus) -> None:
    """The gate render is a real picture of the right place at the wrong size,
    which is exactly the kind of wrong answer that looks right. A scorer that
    asserted nothing about what `expand` drew is handed nothing."""
    judge = Judge(regime=tile_module.CANONICAL_REGIME)
    run = rooted(walk(tmp_path, judge))
    assert run.identity is None, "a deploy-geometry judge makes no claim about the gate render"
    run.run()
    assert judge.offered, "the scorer was never asked anything"
    assert all(batch is None for batch in judge.offered), "it was offered a gate render"


@needs_engine
def test_every_scored_row_says_which_picture_its_verdict_came_off(tmp_path, corpus) -> None:
    """A union that holds ledgers scored at two geometries must never have to
    guess which a row is."""
    from fractal_wallpapers.discovery import ledger as ledger_module

    run = rooted(walk(tmp_path, Judge()))
    run.run()
    run.ledger.close()

    rows = [row for row in ledger_module.read(run.ledger.path) if row["kind"] == "candidate"]
    scored = [row for row in rows if row["score"] is not None]
    assert scored, "the smoke walk scored nothing"
    for row in scored:
        assert row["score_regime"] == NODE.spelled
        assert row["score_view"]
    for row in rows:
        if row["score"] is None:
            assert row["score_regime"] is None, "no picture, no provenance"


# --------------------------------------------------------------------------- #
# The per-run sanity line.
# --------------------------------------------------------------------------- #
def test_the_sample_is_a_reservoir_and_not_a_prefix() -> None:
    """A walk's first batches are its shallowest, so the first hundred survivors
    are a sample of the top of every lineage and of nothing else."""
    sample = identity.Sample(size=10, seed=7)
    for index in range(500):
        sample.offer({"score": 0.5, "maxiter": index})
    assert sample.seen == 500
    assert len(sample.rows) == 10
    assert max(row["maxiter"] for row in sample.rows) > 10, "a prefix holds only the first ten"


def test_the_sample_is_seeded_and_takes_nothing_from_the_walk_s_own_stream() -> None:
    """An insurance line that moved which nodes the frontier popped would not be
    insurance."""
    import random

    def drawn(seed: int) -> list:
        sample = identity.Sample(size=5, seed=seed)
        for index in range(200):
            sample.offer({"score": 0.5, "maxiter": index})
        return [row["maxiter"] for row in sample.rows]

    assert drawn(1) == drawn(1)
    assert drawn(1) != drawn(2), "two runs must not draw the same sample"
    assert identity.Sample(size=5, seed=1).rng is not random, "it draws on its own stream"


def test_an_unscored_survivor_is_never_sampled() -> None:
    """There is nothing to compare a second read against."""
    sample = identity.Sample(size=5, seed=0)
    for _ in range(10):
        sample.offer({"score": None})
    assert (sample.seen, sample.rows) == (0, [])


def test_a_deploy_regime_scorer_has_nothing_to_dual_score_against(tmp_path) -> None:
    """It would be comparing a number with itself."""
    sample = identity.Sample(size=5, seed=0)
    sample.offer({"score": 0.5})

    class Deploy:
        regime = None

    assert identity.dual_score(sample, Deploy(), tmp_path) is None
    assert identity.dual_score(identity.Sample(size=0), Judge(), tmp_path) is None


def test_the_second_read_counts_a_decision_that_moved_at_each_gate(tmp_path) -> None:
    """A flip is the two arms landing on opposite sides of a gate this project
    already acts at — read off the gates' own owners, never restated here."""
    from fractal_wallpapers.models import regime_flips

    sample = identity.Sample(size=4, seed=0)
    for _ in range(4):
        # Above every gate at the node regime; the twin answers 0.5 lower, which
        # on the restated scale is below all three.
        sample.offer({"score": 0.9, "score_great": 0.9, "family": {}, "viewport": {}, "maxiter": 1})

    report = identity.dual_score(sample, Judge(), tmp_path / "flip_sample")
    assert report["regime"] == NODE.spelled
    assert report["against"] == tile_module.CANONICAL_REGIME.spelled
    assert report["compared"] == 4
    assert set(report["flips"]) == {gate["gate"] for gate in regime_flips.gates()}
    assert all(count == 4 for count in report["flips"].values())
    assert "nothing acts on it" in report["line"]


def test_a_survivor_the_second_read_could_not_score_is_counted_and_not_compared(tmp_path) -> None:
    """A failed render is a stated fact, and a flip rate whose denominator quietly
    included it would be a rate over rows nothing looked at."""

    class Blind(Judge):
        def read(self, candidates, pictures=None):
            return [Reading(error="no view") for _ in candidates]

    class Sighted(Judge):
        def at(self, regime, directory):
            return Blind(self.value, regime)

    sample = identity.Sample(size=3, seed=0)
    for _ in range(3):
        sample.offer({"score": 0.9, "score_great": 0.9, "family": {}, "viewport": {}, "maxiter": 1})
    report = identity.dual_score(sample, Sighted(), tmp_path / "flip_sample")
    assert (report["compared"], report["failed"]) == (0, 3)
    assert all(count == 0 for count in report["flips"].values())


def test_the_sanity_line_says_it_is_a_report() -> None:
    """Nothing in a run reads this number, and the line has to say so where it is
    read — a count of flipped decisions beside a run's counters reads like a gate
    unless it says otherwise."""
    said = identity.line({"junk floor": 3, "good floor": 0}, 100, "640x360ss2", 61.4)
    assert "100 survivors" in said and "3 junk floor" in said
    assert "nothing acts on it" in said
    assert "no decision was compared" in identity.line({}, 0, "640x360ss2", 0.0)
