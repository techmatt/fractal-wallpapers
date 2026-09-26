"""The twin channel: does a parameter-plane admission actually become a Julia root,
and does the c-spacing floor act where it says it does.

The last test here is a **real seeded harvest** through the real engine, because
everything above it can be true of a channel nothing ever drew from.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.pools import C_SPACING_FLOOR
from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
from fractal_wallpapers.supply import twins
from fractal_wallpapers.supply.harvest import Budget, Harvest
from fractal_wallpapers.supply.partitions import DYNAMICAL_PLANES
from fractal_wallpapers.supply.refill import Refill
from test_harvest import quota

needs_engine = pytest.mark.skipif(
    not engine.is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)

#: The four twins with no `c`-pool of their own. Not the channel's roster — it
#: serves all five — but the scope most of the refill tests below are built at, so
#: that a test's draws are the derived channel's and nothing else's. The degree-2
#: twin gets its own tests, because what is worth guarding there is the *mixture*.
UNPOOLED_TWINS = ("julia:multibrot3", "julia:multibrot4", "julia:multibrot5", "julia:multibrot6")


def location(plane: str, re: str, im: str = "0.0", width: str = "1e-4") -> dict:
    """One admitted parameter-plane row, as a ledger writes it."""
    family = (
        {"kind": "mandelbrot"}
        if plane == "mandelbrot"
        else {"kind": "multibrot", "degree": int(plane.removeprefix("multibrot"))}
    )
    return {
        "kind": "candidate",
        "fate": ledger_module.SURVIVED,
        "score": 0.9,
        "family": family,
        "viewport": {"center_re": re, "center_im": im, "width": width},
    }


def channel() -> twins.TwinChannel:
    """An unprimed channel, so a test states its own supply rather than inheriting
    whatever corpus this checkout happens to hold."""
    return twins.TwinChannel()


# --------------------------------------------------------------------------- #
# the parameter
# --------------------------------------------------------------------------- #


def test_the_channel_serves_every_twin_including_the_one_with_a_pool() -> None:
    """The degree-2 twin was held out until 2026-09-12 and is the one degree with
    a curated pool, which made it the only one that could not grow: 209 rows, no
    writer, no re-derivation command. What it keeps is a floor, not an exclusion."""
    assert channel().partitions == DYNAMICAL_PLANES
    assert set(twins.POOLED_TWINS) == {"julia:mandelbrot"}
    assert set(twins.POOLED_TWINS) <= set(DYNAMICAL_PLANES)
    assert len(twins.tracked_pool("julia:mandelbrot")) > 0
    assert twins.tracked_pool("julia:multibrot3") == [], "one pooled twin, and it is degree 2"


def test_a_derived_parameter_does_not_displace_a_row_of_the_tracked_pool() -> None:
    """The protection the exclusion carried, kept by the mechanism that was always
    supposed to provide it. Before this the two floors ran over disjoint sets —
    the pool loader over the pool's rows, this channel over its own accepted list,
    which starts empty — so a derived `c` could land on a curated one unseen."""
    live = channel()
    pool = twins.tracked_pool("julia:mandelbrot")
    assert live.reserve("julia:mandelbrot", pool) == len(pool)

    row = pool[0]
    assert live.offer(location("mandelbrot", row.c[0], row.c[1]), "run") is False
    skip = live.skips["julia:mandelbrot"][0]
    assert skip["blocked_by"] == row.id, "the pool row is named, not a seed index"
    assert skip["blocked_by_source"] == "pool"
    assert live.counts()["blocked_by"]["julia:mandelbrot"] == {"pool": 1}
    assert live.seeds("julia:mandelbrot") == [], "a reservation is spacing, never supply"

    # And a `c` the pool does not hold is still derived: this is a floor, not a
    # second exclusion wearing one's clothes.
    assert live.offer(location("mandelbrot", "-5.0", "5.0"), "run") is True
    assert live.counts()["accepted"]["julia:mandelbrot"] == 1


def test_a_c_the_project_has_already_walked_is_counted_and_handed_over_anyway() -> None:
    """The floor refuses a collision with something in the queue. It does not
    refuse history, because nothing else does either — the proven channel dedups
    on the location key alone — and enforcing it here alone would be an asymmetric
    rule dressed up as an invariant. So it is a reading, and it is reported."""
    live = channel()
    walked = {
        "kind": "candidate",
        "family": {"kind": "julia", "degree": 2, "c": ["0.28", "0.008"]},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
    }
    assert live.walked("julia:mandelbrot", walked) is True
    assert live.walked("julia:mandelbrot", walked) is False, "one entry per parameter"

    assert live.offer(location("mandelbrot", "0.28", "0.009"), "run") is True
    assert live.near_walked["julia:mandelbrot"] == 1
    assert live.counts()["near_walked"]["julia:mandelbrot"] == 1
    assert live.summary()["near_walked_sample"]["julia:mandelbrot"][0]["seed_id"] == (
        "twin-mandelbrot-0000"
    )


def test_an_admitted_parent_location_becomes_a_parameter_at_its_own_degree() -> None:
    """The whole channel in one step: the centre of a degree-3 parameter-plane
    find is a `c` for the degree-3 Julia family and for no other."""
    live = channel()
    assert live.offer(location("multibrot3", "0.4", "0.25"), "run") is True
    seed = live.seeds("julia:multibrot3")[0]
    assert seed.c == ("0.4", "0.25")
    assert seed.family(live.degree_of("julia:multibrot3")) == {
        "kind": "julia",
        "degree": 3,
        "c": ["0.4", "0.25"],
    }
    assert live.seeds("julia:multibrot4") == [], "a c belongs to one degree"


def test_a_parameter_inside_the_spacing_floor_is_skipped_and_recorded() -> None:
    """Julia similarity decays with no knee, so the floor is a stated tolerance —
    and a skip nobody can count is indistinguishable from a barren parent."""
    live = channel()
    assert live.offer(location("multibrot4", "0.4", "0.0"), "run") is True
    near = f"{0.4 + C_SPACING_FLOOR / 2:.6f}"
    far = f"{0.4 + C_SPACING_FLOOR * 2:.6f}"
    assert live.offer(location("multibrot4", near), "run") is False
    assert live.offer(location("multibrot4", far), "run") is True

    twin = "julia:multibrot4"
    assert live.counts()["offered"][twin] == 3
    assert live.counts()["accepted"][twin] == 2
    assert live.counts()["skipped_inside_floor"][twin] == 1
    skip = live.summary()["skip_sample"][twin][0]
    assert skip["blocked_by"] == "twin-multibrot4-0000"
    assert skip["distance"] < C_SPACING_FLOOR


def test_a_row_that_is_not_a_parameter_plane_is_not_supply_here() -> None:
    live = channel()
    julia = {
        "kind": "candidate",
        "family": {"kind": "julia", "degree": 3, "c": ["0.1", "0.1"]},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
    }
    assert live.offer(julia, "run") is False
    assert live.note("julia:multibrot3", julia) is False
    assert sum(live.counts()["offered"].values()) == 0


def test_a_parent_with_no_admissions_is_starved_upstream_and_says_so() -> None:
    """Not an error, and not a silence: a twin waiting on its parent is a state,
    and the sentence names the parent that would end it."""
    reason = channel().starvation("julia:multibrot5")
    assert "starved upstream" in reason
    assert "multibrot5" in reason
    assert "not a fault" in reason


def test_a_drawn_out_channel_says_it_was_working_rather_than_starved() -> None:
    live = channel()
    live.offer(location("multibrot3", "0.4"), "run")
    reason = live.starvation("julia:multibrot3", drawn=1)
    assert "exhausted" in reason and "starved upstream" not in reason


def test_only_a_label_the_currency_pays_for_is_a_keeper() -> None:
    assert twins.labelled_keeper({"score": 4}) is True
    assert twins.labelled_keeper({"score": 3}) is True
    assert twins.labelled_keeper({"score": 2}) is False
    assert twins.labelled_keeper({"score": None}) is False


def test_the_channel_state_round_trips_with_its_floor_intact() -> None:
    """A resumed run that forgot its accepted parameters would hand out
    near-duplicates of what it had already spent."""
    live = channel()
    live.offer(location("multibrot3", "0.4"), "labels")
    live.offer(location("multibrot3", "0.9"), "run")
    restored = channel()
    restored.load_state(live.state())
    assert [s.id for s in restored.seeds("julia:multibrot3")] == [
        "twin-multibrot3-0000",
        "twin-multibrot3-0001",
    ]
    assert restored.sources["julia:multibrot3"] == {"labels": 1, "run": 1}
    near = f"{0.4 + C_SPACING_FLOOR / 4:.6f}"
    assert restored.offer(location("multibrot3", near), "run") is False


# --------------------------------------------------------------------------- #
# the channel, inside a refill
# --------------------------------------------------------------------------- #


def refill_of(tmp_path, live) -> tuple[Walk, Refill]:
    """A refill over the four twins alone, so a test's draws are the twins'."""
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    return walk, Refill(
        walk,
        low_water=2,
        per_draw=2,
        twins=live,
        partitions=UNPOOLED_TWINS,
    )


def pooled_refill(tmp_path, live) -> tuple[Walk, Refill]:
    """A refill over the degree-2 twin alone, which is the one with both channels."""
    walk = Walk(out_dir=tmp_path / "run", seed=1, limits=Limits(batch=2))
    return walk, Refill(
        walk,
        low_water=2,
        per_draw=2,
        twins=live,
        partitions=["julia:mandelbrot"],
    )


def test_a_pooled_twins_queue_holds_its_tracked_pool_and_its_derived_parameters(
    tmp_path,
) -> None:
    """*Displace* was literal: this branch is read before the `julia:mandelbrot`
    one, so a served degree-2 twin used to get the derived list instead of the
    pool's rows. One queue, pool first, and neither crowds the other out."""
    live = channel()
    assert live.offer(location("mandelbrot", "-5.0", "5.0"), "run") is True
    assert live.offer(location("mandelbrot", "-6.0", "6.0"), "run") is True
    _, refill = pooled_refill(tmp_path, live)

    pool = twins.tracked_pool("julia:mandelbrot")
    queue = refill._pool("julia:mandelbrot")
    assert len(queue) == len(pool) + 2
    assert queue[0].id == pool[0].id, "the pool leads, one for one"
    assert queue[1].channel.startswith(twins.SEED_CHANNEL)
    assert queue[2].id == pool[1].id


def test_a_parameter_derived_mid_run_lands_behind_the_cursor_and_moves_nothing(
    tmp_path,
) -> None:
    """The cursor is an index, so an entry it has already handed over must not
    move. Re-interleaving a grown derived list moved everything past the old
    exhaustion point down a slot, which walks one root twice and never walks the
    new parameter at all — `interleave` carries the worked example."""
    live = channel()
    live.offer(location("mandelbrot", "-5.0", "5.0"), "run")
    _, refill = pooled_refill(tmp_path, live)
    before = list(refill._pool("julia:mandelbrot"))

    live.offer(location("mandelbrot", "-6.0", "6.0"), "run")
    after = list(refill._pool("julia:mandelbrot"))
    assert after[: len(before)] == before, "the queue grew; it did not shuffle"
    assert len(after) == len(before) + 1
    assert after[-1].id == "twin-mandelbrot-0001", "a parameter derived mid-run is at the tail"


def test_a_pooled_twins_two_kinds_of_seed_keep_their_own_provenance(tmp_path) -> None:
    """Both are a `JuliaSeed` and a branch on the partition would call the pool's
    rows derived, crediting the twin channel with what a three-stage screen found.
    The seed says which channel made it, so the dispatch asks the seed."""
    live = channel()
    live.offer(location("mandelbrot", "-5.0", "5.0"), "run")
    _, refill = pooled_refill(tmp_path, live)

    row = twins.tracked_pool("julia:mandelbrot")[0]
    parameter = refill._root_of("julia:mandelbrot", row, 0)
    assert parameter["source"] == "julia_c_pool"
    assert parameter["provenance"]["channel"] == row.channel
    assert "parent_plane" not in parameter["provenance"]

    derived = refill._root_of("julia:mandelbrot", live.seeds("julia:mandelbrot")[0], 1)
    assert derived["source"] == "twin_channel"
    assert derived["provenance"]["parent_plane"] == "mandelbrot"
    assert derived["family"] == {"kind": "julia", "degree": 2, "c": ["-5", "5"]}


def test_a_twin_with_parameters_is_servable_and_one_without_is_deferred(tmp_path) -> None:
    live = channel()
    live.offer(location("multibrot3", "0.4"), "run")
    walk, refill = refill_of(tmp_path, live)
    queues = dict.fromkeys(UNPOOLED_TWINS, 0)

    assert refill.has_channel("julia:multibrot3") is True
    assert refill.remaining("julia:multibrot3") == 1
    assert refill.starved(queues, batch=0) == ["julia:multibrot3"]
    deferred = refill.deferred(queues)
    assert "julia:multibrot3" not in deferred
    assert "starved upstream" in deferred["julia:multibrot4"]["reason"]


def test_a_draw_pushes_a_julia_root_at_the_parents_degree(tmp_path) -> None:
    """The same `entry.family(degree)` call the tracked degree-2 pool makes —
    one channel more, not a second mechanism."""
    live = channel()
    live.offer(location("multibrot5", "0.4", "0.1"), "run")
    walk, refill = refill_of(tmp_path, live)
    outcome = refill.run(dict.fromkeys(UNPOOLED_TWINS, 0), batch=0, loop_seconds=1.0)

    assert outcome["roots"] == 1
    node = walk.frontier[-1]
    assert node["family"] == {"kind": "julia", "degree": 5, "c": ["0.4", "0.1"]}
    root = [row for row in ledger_module.read(walk.ledger.path) if row["kind"] == "root"][-1]
    assert root["source"] == "twin_channel"
    assert root["provenance"]["parent_plane"] == "multibrot5"
    # The Julia home view, from the engine — no framing literal on this side.
    assert float(node["width"]) > 0.0


def test_the_channel_only_ever_hands_over_what_nobody_has_walked(tmp_path) -> None:
    """A cursor claim, so the loop's clock is declared too long to bind. At a
    one-second loop the first draw's two `engine.home_view` spawns are charged
    against the refill share, and past a third of a second of real time — a
    loaded box, a cold runner — the second draw is refused as over the share and
    the handover under test never happens. The share has its own guard, below,
    on seconds the test states rather than seconds the box spends."""
    live = channel()
    for step in range(3):
        live.offer(location("multibrot3", f"{0.1 + step:.4f}"), "run")
    walk, refill = refill_of(tmp_path, live)
    queues = dict.fromkeys(UNPOOLED_TWINS, 0)
    refill.run(queues, batch=0, loop_seconds=1e6)
    assert refill.remaining("julia:multibrot3") == 1
    refill.run(queues, batch=refill.cooldown, loop_seconds=1e6)
    assert refill.remaining("julia:multibrot3") == 0
    assert len({node["family"]["c"][0] for node in walk.frontier}) == 3


def test_a_refill_over_its_share_of_the_loop_is_refused_and_counted(tmp_path) -> None:
    """The bound the cursor test above declares out of its way, held on stated
    seconds: refills may spend `share` of the loop's whole wall and no more."""
    live = channel()
    live.offer(location("multibrot3", "0.1"), "run")
    walk, refill = refill_of(tmp_path, live)
    refill.seconds = 1.0
    assert refill.affordable(loop_seconds=3.0) is True, "1 of 4 is exactly the share"
    assert refill.affordable(loop_seconds=2.0) is False
    outcome = refill.run(dict.fromkeys(UNPOOLED_TWINS, 0), batch=0, loop_seconds=2.0)
    assert outcome == {"refilled": [], "roots": 0, "reason": "over the refill share"}
    assert refill.deferred_draws == 1
    assert walk.frontier == []


# --------------------------------------------------------------------------- #
# a real, small, seeded run
# --------------------------------------------------------------------------- #


@needs_engine
def test_a_harvest_serves_a_twin_off_a_derived_parameter(tmp_path) -> None:
    """Through the real engine: a channel primed with one parameter per twin is
    served, expands, and reconciles — the path a production run takes once its
    parent planes have admitted anything."""
    live = channel()
    for plane, re in (
        ("multibrot3", "0.4"),
        ("multibrot4", "0.3"),
        ("multibrot5", "0.35"),
        ("multibrot6", "0.3"),
    ):
        assert live.offer(location(plane, re, "0.15"), "labels") is True

    walk = Walk(
        out_dir=tmp_path / "run",
        seed=20260816,
        limits=Limits(batch=6, root_expansions=3),
        policy=Policy(candidates=2, node_width=96),
    )
    run = Harvest(
        walk,
        quota(run_dir=tmp_path / "run", partitions=list(UNPOOLED_TWINS)),
        budget=Budget(minutes=0.0, batches=2),
        batch_size=6,
        refill=Refill(
            walk,
            low_water=2,
            per_draw=2,
            twins=live,
            partitions=UNPOOLED_TWINS,
        ),
        partitions=list(UNPOOLED_TWINS),
    )
    summary = run.run()

    # Served is read off BATCHES, not minutes: a twin's expansion here can finish
    # inside one tick of Windows' 15.6 ms `time.monotonic`, book 0 minutes, and read
    # as unserved — about 1 run in 30 on 2026-09-26.
    served = {p for p, row in summary["quota"]["mix"]["batches"].items() if row["realized"] > 0}
    assert served == set(UNPOOLED_TWINS), "all four twins were servable off derived parameters"
    assert summary["tally"]["found"] > 0
    assert summary["refill"]["twins"]["c_spacing_floor"] == C_SPACING_FLOOR
    # Each twin's one derived parameter has been handed over and walked. That is a
    # channel that worked, and the deferral says so rather than calling it starved.
    for row in summary["refill"]["deferred"].values():
        assert "the twin channel is exhausted" in row["reason"]


@needs_engine
def test_a_resumed_run_keeps_the_parameters_its_floor_was_spaced_against(tmp_path) -> None:
    """A c-spacing floor that forgot half its accepted parameters would hand out
    near-duplicates of what the first session had already spent."""

    def build(batches: int, live) -> Harvest:
        walk = Walk(
            out_dir=tmp_path / "run",
            seed=20260816,
            limits=Limits(batch=4, root_expansions=3),
            policy=Policy(candidates=2, node_width=96),
        )
        return Harvest(
            walk,
            quota(run_dir=tmp_path / "run", partitions=list(UNPOOLED_TWINS)),
            budget=Budget(minutes=0.0, batches=batches),
            batch_size=4,
            refill=Refill(
                walk,
                low_water=2,
                per_draw=2,
                twins=live,
                partitions=UNPOOLED_TWINS,
            ),
            partitions=list(UNPOOLED_TWINS),
        )

    first = channel()
    first.offer(location("multibrot3", "0.4", "0.15"), "labels")
    build(1, first).run()

    # A fresh channel, primed with nothing: only the checkpoint can put the
    # parameter back, and only then can the floor still refuse its near-duplicate.
    second = channel()
    run = build(3, second)
    assert run.resume() is True
    assert [s.id for s in second.seeds("julia:multibrot3")] == ["twin-multibrot3-0000"]
    near = f"{0.4 + C_SPACING_FLOOR / 4:.6f}"
    assert second.offer(location("multibrot3", near, "0.15"), "run") is False
