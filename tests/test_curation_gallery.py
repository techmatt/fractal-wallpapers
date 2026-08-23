"""The gallery pass: the radius, the floors, the location rule, and pass identity.

Every claim here is one a wrong answer would cost a full-resolution render or a
wallpaper of a place the collection already has. The expensive halves — the
attempt leg and the release leg — are not exercised: what is pinned is the
arithmetic between them, which is where every decision the pass takes is made.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy
import pytest

from fractal_wallpapers.curation import (
    durability,
    floors,
    gallery,
    gallery_store,
    records,
    selection,
)
from fractal_wallpapers.supply import partitions


# --------------------------------------------------------------------------- #
# A tiny synthetic pool: unit vectors in a plane, so distances are arithmetic.
# --------------------------------------------------------------------------- #
def unit(angle: float) -> list[float]:
    """A unit vector at `angle` radians, in the first two of four dimensions."""
    return [numpy.cos(angle), numpy.sin(angle), 0.0, 0.0]


def location(key: str, angle: float, partition: str = "mandelbrot") -> dict:
    """One embedded location, spaced by angle so the cosine is `1 - cos(angle)`."""
    return {
        "key": key,
        "partition": partition,
        "family": {"kind": "mandelbrot", "degree": 2},
        # Widths a decade apart and centres far outside each other's frame, so the
        # near-duplicate grouping puts every synthetic location in its own group
        # unless a test deliberately collides two.
        "viewport": {"center_re": str(float(len(key)) + angle), "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "location_p_ge3": 0.9,
        "picture": f"{key}.jpg",
    }


def matrix_of(rows: list[dict], angles: list[float]):
    return numpy.array([unit(angle) for angle in angles], dtype=numpy.float32)


def candidate(
    identifier: str,
    key: str,
    head: str,
    p_ge3: float,
    p_ge4: float = 0.5,
    partition: str = "mandelbrot",
    center: str = "0",
) -> dict:
    """One flat candidate row, in the shape the seating compares."""
    return {
        "candidate": identifier,
        "source": {"run": "run9", "candidate": identifier, "key": None},
        "head": head,
        "partition": partition,
        "key": key,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": center, "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": "viridis",
        "p_ge3": p_ge3,
        "p_ge4": p_ge4,
    }


SMOOTH, STRANGE = "smooth_render", "strange_render"


# --------------------------------------------------------------------------- #
# Step 4: the hard radius.
# --------------------------------------------------------------------------- #
def test_the_hard_radius_refuses_a_point_however_good_it_is() -> None:
    """Quality never buys a seat inside the radius. That is what makes it hard."""
    angles = [0.0, 0.02, 1.0]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    # The best location by a distance is the one 0.02 radians from the first —
    # about 0.0002 cosine distance away, well inside any sane radius.
    quality = [0.5, 0.99, 0.1]
    picks, tally = gallery.choose(range(3), matrix, quality, 3, 0.05, 1.0)
    assert [pick.index for pick in picks] == [1, 2]
    assert tally["refused_by_radius"] == 1


def test_a_partition_that_runs_out_of_eligible_points_returns_fewer() -> None:
    """Not an error and not padding: the pool does not hold that many places."""
    angles = [0.0, 0.001, 0.002]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    picks, tally = gallery.choose(range(3), matrix_of(rows, angles), [1.0] * 3, 3, 0.05, 1.0)
    assert len(picks) == 1
    assert tally["chosen"] == 1
    assert tally["eligible"] == 3


def test_the_first_pick_is_the_strongest_and_the_rest_are_gain_weighted() -> None:
    angles = [0.0, 0.8, 1.6]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [0.1, 0.9, 0.2], 3, 0.01, 1.0)
    assert picks[0].index == 1  # strongest by quality, with nothing to be far from
    assert picks[0].distance is None
    assert {pick.index for pick in picks} == {0, 1, 2}
    assert all(pick.distance >= 0.01 for pick in picks[1:])


def test_a_zero_quality_weight_is_pure_farthest_point() -> None:
    """gamma of zero takes the judge out of the draw entirely."""
    angles = [0.0, 0.4, 2.4]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [0.9, 0.9, 0.001], 2, 0.01, 0.0)
    # Second pick is the farthest one, not the second-best one.
    assert picks[1].index == 2


def test_the_retro_table_is_the_nearest_pairs_closest_first() -> None:
    angles = [0.0, 0.5, 1.9]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    picks, _ = gallery.choose(range(3), matrix, [1.0, 1.0, 1.0], 3, 0.01, 1.0)
    table = gallery.retro_table(picks, matrix)
    assert len(table) == 3
    assert table == sorted(table, key=lambda cell: cell["cosine_distance"])


def test_the_neighbourhood_keeps_the_chosen_point_whatever_its_quality() -> None:
    angles = [0.0, 0.05, 0.06, 3.0]
    rows = [location(f"k{i}", angle) for i, angle in enumerate(angles)]
    matrix = matrix_of(rows, angles)
    near = gallery.neighbourhood(0, range(4), matrix, [0.01, 0.9, 0.8, 0.9], 3, 0.05)
    assert near[0] == 0
    assert set(near) == {0, 1, 2}


# --------------------------------------------------------------------------- #
# Step 6: the floors, one wallpaper per location, and unfilled slots.
# --------------------------------------------------------------------------- #
def slot(identifier: str, head: str, keys: list[str], partition: str = "mandelbrot"):
    return gallery.Slot(
        id=identifier, partition=partition, head=head, point=keys[0], locations=list(keys)
    )


def test_both_measured_floors_act_in_the_pass_and_only_one_acts_at_a_release() -> None:
    """The one place a head's cut reads differently at two sites, on purpose."""
    assert set(floors.MEASURED_RELEASE_FLOORS) == {SMOOTH, STRANGE}
    assert set(floors.ACTING_RELEASE_BARS) == {STRANGE}
    assert floors.release_bar(SMOOTH) is None
    assert floors.gallery_floor(SMOOTH).value == floors.SMOOTH_RELEASE_FLOOR.value
    assert floors.gallery_floor(STRANGE).value == floors.STRANGE_RELEASE_BAR.value


def test_a_head_with_no_measured_floor_cannot_fill_a_gallery_slot() -> None:
    with pytest.raises(ValueError, match="no release floor has been measured"):
        floors.gallery_floor("a_head_nobody_fit")


def test_each_floor_acts_on_its_own_head_and_neither_reaches_the_other() -> None:
    """A smooth candidate at 0.4 seats; a strange one at 0.4 does not, and the
    numbers are never compared to each other."""
    smooth_floor = floors.gallery_floor(SMOOTH).value
    strange_floor = floors.gallery_floor(STRANGE).value
    assert smooth_floor < 0.4 < strange_floor
    slots = [slot("0000", SMOOTH, ["a"]), slot("0001", STRANGE, ["b"])]
    gallery.seat(
        slots,
        [
            candidate("s", "a", SMOOTH, 0.4, center="0"),
            candidate("t", "b", STRANGE, 0.4, center="90"),
        ],
        log=lambda _line: None,
    )
    assert slots[0].seated is not None
    assert slots[1].seated is None
    assert slots[1].unfilled == "below_bar"
    assert slots[1].fill["below_floor"] == 1


def test_a_slot_with_nothing_above_the_floor_is_unfilled_and_never_padded() -> None:
    slots = [slot("0000", STRANGE, ["a"])]
    report = gallery.seat(
        slots,
        [candidate(str(i), "a", STRANGE, 0.1 + i / 100) for i in range(5)],
        log=lambda _line: None,
    )
    assert slots[0].seated is None
    assert slots[0].unfilled == "below_bar"
    assert slots[0].fill["why"] == selection.UNFILLED_REASONS["below_bar"]
    assert report["filled"] == 0
    assert report["unfilled"] == 1


def test_a_slot_with_no_candidate_at_all_says_so_rather_than_below_the_floor() -> None:
    slots = [slot("0000", STRANGE, ["nobody"])]
    gallery.seat(slots, [], log=lambda _line: None)
    assert slots[0].unfilled == "no_candidates"


def test_one_wallpaper_per_location_across_the_whole_pass() -> None:
    """Two slots wanting one place seat one wallpaper between them, and the
    higher-ranked slot keeps it."""
    slots = [slot("0000", SMOOTH, ["a"]), slot("0001", SMOOTH, ["a"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [
            candidate("weak", "a", SMOOTH, 0.9, p_ge4=0.2),
            candidate("strong", "a", SMOOTH, 0.9, p_ge4=0.9),
        ],
        log=lambda _line: None,
    )
    assert floors.CLUSTER_CAP == 1
    seated = [s for s in slots if s.seated]
    assert len(seated) == 1
    assert seated[0].seated["candidate"] == "strong"
    empty = [s for s in slots if not s.seated][0]
    assert empty.unfilled == selection.LOCATION_SERVED
    assert report["filled"] == 1


def test_ranking_is_p_ge4_first_and_p_ge3_only_breaks_the_tie() -> None:
    ordered = sorted(
        [
            candidate("a", "k", SMOOTH, 0.99, p_ge4=0.10),
            candidate("b", "k", SMOOTH, 0.40, p_ge4=0.80),
            candidate("c", "k", SMOOTH, 0.90, p_ge4=0.80),
        ],
        key=gallery.rank_key,
    )
    assert [row["candidate"] for row in ordered] == ["c", "b", "a"]


def test_a_candidate_with_no_fourth_class_sorts_below_one_that_has_it() -> None:
    """Three-class rows exist in the pool; they are not read as a zero."""
    rows = sorted(
        [
            candidate("old", "k", STRANGE, 0.99, p_ge4=None),
            candidate("new", "k", STRANGE, 0.70, p_ge4=0.01),
        ],
        key=gallery.rank_key,
    )
    assert [row["candidate"] for row in rows] == ["new", "old"]


# --------------------------------------------------------------------------- #
# Steps 1 and 2: slots and the head split.
# --------------------------------------------------------------------------- #
def test_the_head_split_is_taken_per_partition() -> None:
    assert gallery.head_split(5, 0.6) == {SMOOTH: 2, STRANGE: 3}
    assert gallery.head_split(1, 0.6) == {SMOOTH: 0, STRANGE: 1}


def test_the_head_order_holds_both_heads_near_their_share_at_every_prefix() -> None:
    order = gallery.head_order({SMOOTH: 2, STRANGE: 3})
    assert sorted(order) == sorted([SMOOTH] * 2 + [STRANGE] * 3)
    assert order[0] == STRANGE
    assert order.count(SMOOTH) == 2


def test_the_pool_wide_denominator_is_every_embedded_location() -> None:
    rows = [location("a", 0.0), location("b", 1.0), location("c", 2.0, "phoenix")]
    assert gallery.population(rows) == {"mandelbrot": 2, "phoenix": 1}


# --------------------------------------------------------------------------- #
# Pass identity.
# --------------------------------------------------------------------------- #
@pytest.fixture
def record_root(tmp_path, monkeypatch):
    """Every record this process writes, redirected under `tmp_path`.

    Both halves of the store, because the pass now writes to two trees: the
    tracked one under `data/` that [`records.root`] names, and the untracked
    attempt store beside it. A fixture that redirected one of the two would leave
    a test writing pool rows into the live `artifacts/`.
    """
    monkeypatch.setattr(records, "_ROOT", (tmp_path / "curation").resolve())
    monkeypatch.setattr(gallery_store, "store_root", lambda: tmp_path / "gallery_store")
    monkeypatch.setattr(
        gallery_store,
        "backup_path",
        lambda pass_id: tmp_path / "backup" / str(pass_id) / gallery_store.STORE_NAME,
    )
    monkeypatch.setattr(durability, "rehome", lambda stored: None)
    return tmp_path / "curation"


def test_two_passes_leave_two_records_and_the_first_is_untouched(record_root) -> None:
    first = gallery.write_pass("gallery1", {"schema": 1, "pass": "gallery1", "seating": {}})
    before = first.read_text(encoding="utf-8")
    second = gallery.write_pass("gallery2", {"schema": 1, "pass": "gallery2", "seating": {}})
    assert first != second
    assert first.read_text(encoding="utf-8") == before
    assert json.loads(second.read_text(encoding="utf-8"))["pass"] == "gallery2"
    assert gallery.passes() == ["gallery1", "gallery2"]


def test_a_pass_record_lives_beside_the_runs_and_not_among_them(record_root) -> None:
    """A pass books no clock and measures no release rate, so it writes no run row."""
    gallery.write_pass("gallery1", {"schema": 1, "pass": "gallery1"})
    assert gallery.record_path("gallery1").parent.parent.name == "gallery"
    assert not (record_root / "runs").exists()
    assert not (record_root / "runs.jsonl").exists()


def test_the_next_pass_id_is_the_next_unused_ordinal(record_root) -> None:
    assert gallery.next_pass_id() == "gallery1"
    gallery.write_pass("gallery1", {"schema": 1})
    assert gallery.next_pass_id() == "gallery2"
    gallery.write_pass("gallery7", {"schema": 1})
    assert gallery.next_pass_id() == "gallery8"


def test_a_pass_stamps_its_release_rows_with_the_gallery_collection(record_root) -> None:
    slots = [slot("0000", SMOOTH, ["a"])]
    gallery.seat(slots, [candidate("0000", "a", SMOOTH, 0.9, p_ge4=0.9)], log=lambda _l: None)
    slots[0].seated["release_picture"] = "release/0000.png"
    attempt = {
        "attempt": 0,
        "head": SMOOTH,
        "partition": "mandelbrot",
        "key": "a",
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "0", "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": "viridis",
        "p_ge3": 0.9,
        "p_ge4": 0.9,
        "picture": "pictures/0000.jpg",
    }
    # The seated candidate carries the same id as the attempt, so the pass writes
    # one row for it rather than two.
    slots[0].seated["candidate"] = "0000"
    written = gallery.write_records("gallery1", slots, [attempt], ["mandelbrot"], lambda _l: None)
    assert written["release_rows"] == 1
    rows = records.read_decisions(records.RELEASE, "gallery1")
    assert [row["collection"] for row in rows] == [records.GALLERY]
    assert rows[0]["verdict"] == records.RELEASED
    assert rows[0]["slot"]["pass"] == "gallery1"
    assert rows[0]["slot_source"] == "guarantee"


# --------------------------------------------------------------------------- #
# The naming rule, at the one place a new module could reintroduce a retired name.
# --------------------------------------------------------------------------- #
def test_the_gallery_pass_carries_none_of_the_retired_vocabulary() -> None:
    """`test_banned_vocabulary` covers the tree; this says it out loud where the
    rename actually happened — the design this module is built from was called
    something else until 2026-08-22."""
    banned = re.compile(r"(?<![a-z])emissio[n](?![a-z])", re.IGNORECASE)
    for path in (
        Path("src/fractal_wallpapers/curation/gallery.py"),
        Path("src/fractal_wallpapers/curation/floors.py"),
        Path("src/fractal_wallpapers/cli.py"),
    ):
        assert not banned.search(path.read_text(encoding="utf-8")), path


# --------------------------------------------------------------------------- #
# The store split: what a pass puts in the history, and what it puts beside it.
# --------------------------------------------------------------------------- #
#: The per-file ceiling `tests/test_history_purity.py` holds every tracked file to.
MAX_TRACKED_BYTES = 1024 * 1024


def attempt(number: int, key: str, head: str, partition: str = "mandelbrot") -> dict:
    """One attempt row in the shape `colorize.annotate` hands back."""
    return {
        "attempt": number,
        "head": head,
        "partition": partition,
        "key": key,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": key, "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": "viridis",
        "anchor": "twilight",
        "candidates": [f"map{i}" for i in range(8)],
        "candidate_scores": {f"map{i}": 0.5 for i in range(8)},
        "location_score": 0.9,
        "p_ge2": 0.95,
        "p_ge3": 0.9,
        "p_ge4": 0.6,
        "rank_score": 0.6,
        "picture": f"pictures/{number:04d}.jpg",
    }


def seated_slot(number: int, key: str, head: str, partition: str = "mandelbrot"):
    """One filled slot, seating this pass's own attempt `number`."""
    filled = slot(f"{number:04d}", head, [key, f"{key}n1", f"{key}n2"], partition)
    filled.point_index = number
    filled.seated = {
        **gallery.candidate_of_attempt(attempt(number, key, head, partition), "gallery1"),
        "group": number,
        "release_picture": f"release/{number:04d}.png",
    }
    return filled


def tracked_total(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def test_a_pass_writes_its_attempts_beside_the_history_and_its_winners_into_it(
    record_root,
) -> None:
    """One attempt row per attempt, untracked; one release row per SEAT, tracked."""
    attempts = [attempt(n, f"k{n}", SMOOTH) for n in range(40)]
    slots = [seated_slot(0, "k0", SMOOTH), seated_slot(7, "k7", SMOOTH)]
    written = gallery.write_records("gallery1", slots, attempts, ["mandelbrot"], lambda _l: None)

    assert written["attempts"]["rows"] == 40
    assert len(gallery_store.read("gallery1")) == 40
    assert gallery_store.manifest_path("gallery1").is_file()

    assert written["release_rows"] == 2
    rows = records.read_decisions(records.RELEASE, "gallery1")
    assert [row["candidate"] for row in rows] == ["0000", "0007"]
    assert {row["verdict"] for row in rows} == {records.RELEASED}
    # The half that used to be 1,120 rows of tracked text: nothing the pass passed
    # over is in the history, and the gate directory a pass used to fill is gone.
    assert not records.decisions_dir(records.GATE, "gallery1").exists()


def test_what_a_slot_passed_over_is_still_on_the_record_as_a_count() -> None:
    """The denominator survives the rows: it moves onto the slot, not out of the store."""
    slots = [slot("0000", SMOOTH, ["a"])]
    below = candidate("0001", "a", SMOOTH, 0.01, p_ge4=0.01)
    gallery.seat(slots, [below], log=lambda _l: None)
    assert slots[0].seated is None
    written = gallery._slot_record(slots[0])
    assert written["unfilled"] == "below_bar"
    assert written["fill"]["eligible"] == 1
    assert written["fill"]["below_floor"] == 1


#: Every registered partition, so a synthetic plan spreads its rows over the file
#: axis the tracked store splits on rather than piling them all into one file and
#: measuring a case that cannot happen.
REGISTERED = list(partitions.ALL_PARTITIONS)


def synthetic_pass(extra: int) -> dict:
    """A 500-slot plan, each slot seating its own attempt, plus `extra` that lost.

    Writes the whole record the way a pass does — the slot rows included, through
    `_slot_record`, so what the pin measures is the real per-slot cost and not a
    stub standing in for it.
    """
    where = [REGISTERED[n % len(REGISTERED)] for n in range(500 + extra)]
    slots = [seated_slot(n, f"k{n}", SMOOTH if n % 2 else STRANGE, where[n]) for n in range(500)]
    attempts = [attempt(n, f"k{n}", SMOOTH if n % 2 else STRANGE, where[n]) for n in range(500)]
    attempts += [
        attempt(1000 + n, f"k{n % 500}n{n}", SMOOTH if n % 2 else STRANGE, where[500 + n])
        for n in range(extra)
    ]
    written = gallery.write_records("gallery1", slots, attempts, ["mandelbrot"], lambda _l: None)
    gallery.write_pass(
        "gallery1",
        {
            "schema": 1,
            "pass": "gallery1",
            "records": written,
            "slots": [gallery._slot_record(one) for one in slots],
        },
    )
    return written


def test_the_tracked_bytes_of_a_pass_do_not_move_with_the_attempt_count(
    tmp_path, monkeypatch
) -> None:
    """THE pin on the store split. Ten times the attempts, the same history.

    The two runs write the same 500 seats and differ only in how many attempts
    lost. Everything tracked comes out the same size to within the manifest's own
    row count — a few digits — while the untracked store grows by an order of
    magnitude. A pass that duplicated its attempts as release rows would fail this
    by megabytes.
    """
    sizes, stores = [], []
    for index, extra in enumerate((1_200, 12_000)):
        here = tmp_path / f"run{index}"
        monkeypatch.setattr(records, "_ROOT", (here / "curation").resolve())
        monkeypatch.setattr(gallery_store, "store_root", lambda here=here: here / "store")
        monkeypatch.setattr(
            gallery_store,
            "backup_path",
            lambda pass_id, here=here: here / "backup" / str(pass_id) / gallery_store.STORE_NAME,
        )
        monkeypatch.setattr(durability, "rehome", lambda stored: None)
        written = synthetic_pass(extra)
        sizes.append(tracked_total(here / "curation"))
        stores.append(written["attempts"]["bytes"])

    assert stores[1] > 6 * stores[0]
    assert abs(sizes[1] - sizes[0]) < 64, (sizes, stores)


def test_every_tracked_file_a_five_hundred_slot_pass_writes_clears_the_history_guard(
    record_root,
) -> None:
    """The largest tracked file at N=500, against the 1 MiB the history refuses over."""
    synthetic_pass(12_000)
    files = {path: path.stat().st_size for path in record_root.rglob("*") if path.is_file()}
    # A file of winners and a file of slots per partition, plus the record and the
    # store's manifest.
    assert len(files) == 2 * len(REGISTERED) + 2
    largest = max(files.values())
    assert largest < MAX_TRACKED_BYTES, {str(key): size for key, size in files.items()}


def test_a_later_pass_can_seat_what_an_earlier_pass_attempted(record_root) -> None:
    """An earlier pass's attempts are standing pool candidates, out of the new store."""
    gallery.write_records(
        "gallery1", [], [attempt(3, "a", SMOOTH)], ["mandelbrot"], lambda _l: None
    )
    standing = gallery.pool_candidates([slot("0000", SMOOTH, ["a"])], "gallery2")
    assert [row["candidate"] for row in standing] == ["gallery1_0003"]
    # `source.key` is the POOL ROW's key, which is what `rescore` joins on — not
    # the location's, which is on the candidate itself.
    assert standing[0]["source"] == {
        "run": "gallery1",
        "candidate": "0003",
        "key": "gallery1|gate|0003",
    }
    # Its own attempts are never read back: they are already in hand.
    assert gallery.pool_candidates([slot("0000", SMOOTH, ["a"])], "gallery1") == []


def test_a_pass_refuses_to_run_against_the_layout_that_predates_the_split(record_root) -> None:
    records.write_decisions(
        records.GATE,
        "gallery1",
        [
            records.decision(
                run="gallery1",
                stage=records.GATE,
                candidate="0000",
                verdict="kept",
                row=attempt(0, "a", SMOOTH),
            )
        ],
    )
    with pytest.raises(gallery_store.LayoutRefused, match="predates the store split"):
        gallery_store.refuse_old_layout("gallery1")


def test_migrating_moves_the_attempts_out_and_drops_the_passed_over_duplicates(
    record_root,
) -> None:
    records.write_decisions(
        records.GATE,
        "gallery1",
        [
            records.decision(
                run="gallery1",
                stage=records.GATE,
                candidate=f"{n:04d}",
                verdict="kept",
                row=attempt(n, f"k{n}", SMOOTH),
            )
            for n in range(20)
        ],
    )
    records.write_decisions(
        records.RELEASE,
        "gallery1",
        [
            records.decision(
                run="gallery1",
                stage=records.RELEASE,
                candidate=f"{n:04d}",
                verdict=records.RELEASED if n == 0 else records.PASSED_OVER,
                collection=records.GALLERY,
                row=attempt(n, f"k{n}", SMOOTH),
                picture=f"release/{n:04d}.png" if n == 0 else None,
            )
            for n in range(20)
        ],
    )

    report = gallery_store.migrate("gallery1", log=lambda _l: None)
    assert report == {"pass": "gallery1", "moved": 20, "dropped": 19, "kept": 1}
    assert not records.decisions_dir(records.GATE, "gallery1").exists()
    assert [row["candidate"] for row in records.read_decisions(records.RELEASE, "gallery1")] == [
        "0000"
    ]
    assert len(gallery_store.read("gallery1")) == 20
    assert gallery_store.check("gallery1", log=lambda _l: None)["verdict"] == "ok"
    # Idempotent: the layout is clean now, so a second call finds nothing and the
    # pass no longer refuses.
    assert gallery_store.migrate("gallery1", log=lambda _l: None)["moved"] == 0
    gallery_store.refuse_old_layout("gallery1")


def test_a_pass_record_reads_back_whole_out_of_its_own_directory(record_root) -> None:
    """The slots live a file per partition; a reader still gets one record."""
    slots = [
        seated_slot(0, "k0", SMOOTH, "mandelbrot"),
        seated_slot(1, "k1", STRANGE, "phoenix"),
        seated_slot(2, "k2", SMOOTH, "mandelbrot"),
    ]
    gallery.write_pass(
        "gallery1",
        {"schema": 1, "pass": "gallery1", "slots": [gallery._slot_record(one) for one in slots]},
    )
    assert gallery.record_path("gallery1").is_file()
    assert sorted(path.name for path in gallery.pass_record_dir("gallery1").glob("*.jsonl")) == [
        "mandelbrot.jsonl",
        "phoenix.jsonl",
    ]
    back = gallery.read_pass("gallery1")
    assert [row["id"] for row in back["slots"]] == ["0000", "0001", "0002"]
    assert gallery.passes() == ["gallery1"]
    # The summary says how many slots there are and where they went, so nothing has
    # to glob to know whether it read them all.
    summary = json.loads(gallery.record_path("gallery1").read_text(encoding="utf-8"))
    assert summary["slots"]["count"] == 3
    assert len(summary["slots"]["files"]) == 2


def test_a_seated_slot_does_not_carry_the_release_renders_autolevel_stamp(record_root) -> None:
    """A kilobyte of operator provenance, already on the release row of the same id."""
    filled = seated_slot(0, "k0", SMOOTH)
    filled.seated["release_autolevel"] = {"operator": "band_autolevel/v1", "curve": [0] * 200}
    assert "release_autolevel" not in gallery._slot_record(filled)["seated"]


def test_an_embedding_row_reaches_the_colorizer_with_its_ledger_and_its_score() -> None:
    """Two spellings that do not line up write `null` and say nothing about it."""
    from fractal_wallpapers.curation import colorize

    row = {
        **location("a", 0.0),
        "ledger": "artifacts/harvest_run10/walk.jsonl",
        "location_p_ge3": 0.87,
    }
    spelled = gallery.colorize_row(row)
    assert spelled["_ledger"] == "artifacts/harvest_run10/walk.jsonl"
    assert spelled["score"] == 0.87
    # The two names the colorizer actually reads, off its own source rather than
    # off this test's memory of them.
    source = Path(colorize.__file__).read_text(encoding="utf-8")
    assert '"ledger": row.get("_ledger")' in source
    assert '"location_score": row.get("score")' in source
