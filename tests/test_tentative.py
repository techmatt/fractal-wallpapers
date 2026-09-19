"""The recorded gallery: that its IDs resolve, and that nothing can sweep them.

Two claims are this file's whole reason. **An ID resolves** — every key a record
names comes back as a row and a recipe, by the full key and by the short alias,
and the aliases are unique so that one alias never names two pictures. And
**retention keeps what a record names**: a seat that the top-K rank drops is kept
by [`candidate_ledger.RETAINED_TENTATIVE`], with its picture, because a recorded
gallery is a promise that the picture is still there next week and there is no way
to notice it being broken.

Everything here is synthetic. The record this reads is a solve record's `seated`
list, which [`test_solve`] pins the shape of; nothing in this file renders,
solves, or opens a picture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_candidate_ledger import decision, isolated  # noqa: F401  (a fixture)

from fractal_wallpapers import cli
from fractal_wallpapers.curation import (
    candidate_ledger,
    colorize,
    page_order,
    recipes,
    tentative,
)


def seat(key: str, **over) -> dict:
    """One seat in the shape [`solve._seated`] writes, with `over` applied on top."""
    row = {
        "key": key,
        "seated_for": "general_pool",
        "rank": 0.5,
        "location": f"place-of-{key}",
        "partition": "mandelbrot",
        "mode": "smooth",
        "mode_params": {},
        "kind": "strange_render",
        "palette_group": "map:viridis",
        "cells": ["dark_vivid_green", "light_muted_lime"],
        "families": ["green", "lime"],
        "p_ge4": 0.9,
        "p_ge3": 0.95,
        "above_bar": True,
        # A place nobody has scored, which is what `None` means here and is why it
        # is not `False` — see the comment on the column in [`solve._seated`].
        "spiral": False,
        "p_spiral": None,
        "picture": f"artifacts/curation/depth/a_leg/pictures/{key}.jpg",
    }
    row.update(over)
    return row


def record_of(*seats, n: int = 10) -> dict:
    """A solve record thinned to what [`tentative`] reads off one."""
    return {
        "config": {"n": n, "sort_key": "rank_key"},
        "filled": len(seats),
        "seated": list(seats),
        "pool": {"reachable_clusters": 99, "refused": {}},
        "shortfalls": {"seats": {"asked": n, "filled": len(seats)}},
        "taken_at": "2026-09-02T00:00:00Z",
        "seconds": 1.0,
    }


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def recipes_beside(stamp: str, *keys: str) -> Path:
    """The record's own `recipes.jsonl`, written for the keys named.

    A record with neither this nor a candidate ledger behind it is one the
    resolver **refuses**, and rightly: `"recipe": null` with exit 0 says *this
    seat has no recipe* where the truth is *this machine has nothing to look it
    up in*. So a test that wants a resolvable record gives it one of the two, and
    this is the tracked one — the half a clone actually has.
    """
    from fractal_wallpapers.curation import recipes as recipes_module

    recipe = recipes_module.of_decision(decision()).record()
    path = tentative.recipes_path(stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in keys:
            handle.write(
                json.dumps({"schema": tentative.SCHEMA, "key": key, "recipe": recipe}) + "\n"
            )
    return path


@pytest.fixture
def store(tmp_path, monkeypatch):
    """The whole regenerable tree in `tmp_path`, so a record lands nowhere real.

    The tier redirect and not a patch of `tentative.gallery_dir`: the page's
    thumbnail paths, the picture the prune unlinks and the store the protection
    reads all resolve through the same root, and moving one of them alone would
    leave the others pointing at this machine.
    """
    from fractal_wallpapers import paths

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir()
    # Every synthetic record is published, because `PUBLISHED` names the stamps of
    # this machine and a test writes stamps of its own. Without this an unstamped
    # read would refuse in here for a reason no test in this file is about. The
    # gate itself is tested below against `PUBLISHED` directly.
    monkeypatch.setattr(tentative, "published", tentative.stamps)
    return tmp_path / "artifacts"


@pytest.fixture
def tentative_store(tmp_path, monkeypatch):
    """The recorded-gallery store alone, in `tmp_path`.

    The lighter of the two redirects, and the one a prune has to use: `prune`
    reads the supply sidecar, the fitted population and the served-location index
    off this machine, exactly as `tests/test_candidate_ledger` lets it, so moving
    the whole tree under it would fail on a file the rule under test never reads.

    **The pinned list is redirected with it**, since 2026-09-19: `protected_keys`
    keeps every pinned row as well as every kept record's, and the tracked list
    names real keys that no guard here wrote. `tests/test_pins.py` holds the pins'
    half of the protection.
    """
    from fractal_wallpapers.curation import pins

    monkeypatch.setattr(tentative, "store_root", lambda: tmp_path / "tentative")
    monkeypatch.setattr(pins, "resolved_path", lambda: tmp_path / "no_pins.json")
    return tmp_path / "tentative"


@pytest.fixture(autouse=True)
def no_walk_ledgers(monkeypatch):
    """No location is `centered`, because no walk ledger is in reach of a test.

    Stated rather than relied on: [`depth.centered_locations`] sweeps every
    ledger this machine holds, and a test that let it do so would be reading
    Matt's tree and would take seconds doing it.
    """
    from fractal_wallpapers.curation import depth

    monkeypatch.setattr(depth, "centered_locations", frozenset)


@pytest.fixture(autouse=True)
def no_embedding_store(monkeypatch, tmp_path):
    """No page here reaches the neutral embedding store, for `no_walk_ledgers`' reason.

    [`page`] joins it for [`page_order`]'s distance term, and this machine's copy is
    **71 MB over 41,415 rows** — 1.4 s to stream cold. A fixture row carrying a
    `location` would pay that per test, silently, and the tests in this file are
    about the store of records rather than about the order.

    Redirected at the accessor [`page_order.vectors_for`] reads, which is the tier
    root for this one store: `embeddings.store_path` is `under("curation") /
    STORE_NAME` and is the module's single spelling of it, so a path under
    `tmp_path` cannot be read past. The order still runs — on its attribute terms,
    which is what a clone gets — so these tests exercise the shipped fallback.
    """
    from fractal_wallpapers.curation import embeddings

    monkeypatch.setattr(embeddings, "store_path", lambda: tmp_path / "no_embeddings.jsonl")


# --------------------------------------------------------------------------- #
# The aliases.
# --------------------------------------------------------------------------- #
def test_an_alias_is_eight_characters_until_two_keys_share_them():
    """The short name is the point — a person types it — and the lengthening is
    what stops it naming two pictures. Only the colliding group pays: a key
    nobody shares a prefix with keeps its eight."""
    named = tentative.aliases(["aaaaaaaa1111", "aaaaaaaa2222", "bbbbbbbb0000"])

    assert named["bbbbbbbb0000"] == "bbbbbbbb"
    assert named["aaaaaaaa1111"] == "aaaaaaaa1"
    assert named["aaaaaaaa2222"] == "aaaaaaaa2"


def test_aliases_are_unique_and_do_not_depend_on_the_order_the_keys_arrived_in():
    """An alias printed in a report has to name the same picture when the record
    is read again, and the rows can be re-sorted between those two readings."""
    keys = ["ffff000011", "ffff000012", "ffff000099", "0000abcd", "0000abce00"]

    named = tentative.aliases(keys)
    reversed_order = tentative.aliases(list(reversed(keys)))

    assert named == reversed_order
    assert len(set(named.values())) == len(keys), "two pictures cannot share one alias"


def test_a_lengthened_alias_cannot_collide_with_a_short_one():
    """The property the lengthening rests on: a longer alias begins with a prefix
    only its own colliding group holds, so it can never equal another group's."""
    named = tentative.aliases(["abcdefgh", "abcdefgh1", "abcdefgh2"])

    assert len(set(named.values())) == 3
    assert named["abcdefgh"] == "abcdefgh"


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def test_a_row_carries_the_leading_dominant_colour_and_every_one_the_picture_holds():
    """Both, and for different readers. A person means the leading one by "the
    green one", and the browser filters on the whole list — dominance is
    thresholded, so filtering on the leading cell alone would hide a green
    picture from the green filter whenever another colour happened to lead it."""
    rows = tentative.rows_of(record_of(seat("k0")))

    assert rows[0]["cell"] == "dark_vivid_green"
    assert rows[0]["hue_family"] == "green"
    assert rows[0]["cells"] == ["dark_vivid_green", "light_muted_lime"]
    assert rows[0]["families"] == ["green", "lime"]


def floors_of(**per_cell) -> dict:
    """A record's `shortfalls.cell_floors` block, thinned to what `rows_of` reads."""
    return {
        "per_cell": {
            cell: {"floor": floor, "seated": seated} for cell, (floor, seated) in per_cell.items()
        }
    }


def test_a_seat_the_colour_floor_bought_does_not_look_like_every_other_seat():
    """The evaluation question the sheet is read to answer is *what did the floor
    drag in*, and it cannot be answered off a page where a floor-mandated seat is
    indistinguishable from one the ranked walk placed."""
    record = record_of(seat("k0", seated_for="cell_floor:dark_vivid_green"))
    record["shortfalls"]["cell_floors"] = floors_of(dark_vivid_green=(20, 20))

    row = tentative.rows_of(record)[0]
    assert row["seated_for"] == "cell_floor:dark_vivid_green"
    assert row["floor"] == tentative.FLOOR_MANDATED
    assert row["floor_cells"] == ["dark_vivid_green"]


def test_a_seat_another_leg_placed_that_the_floor_now_HOLDS_is_a_third_answer():
    """*What did the floor drag in* and *what is the floor now paying for* are two
    questions. A swap or a chain can replace a mandated seat with one of its own,
    and the floor is still why a seat of that colour is there — so a seat charging
    a cell at or below its floor is marked, and marked differently."""
    record = record_of(seat("k0", seated_for="swap"))
    record["shortfalls"]["cell_floors"] = floors_of(
        dark_vivid_green=(20, 20), light_muted_lime=(20, 41)
    )

    row = tentative.rows_of(record)[0]
    assert row["floor"] == tentative.FLOOR_HOLDING
    assert row["floor_cells"] == ["dark_vivid_green"], "the cell above its floor is not one"


def test_a_seat_in_no_cell_the_floor_is_short_of_is_free_of_it():
    record = record_of(seat("k0", seated_for="general_pool"))
    record["shortfalls"]["cell_floors"] = floors_of(
        dark_vivid_green=(20, 63), light_muted_lime=(20, 41)
    )

    assert tentative.rows_of(record)[0]["floor"] == tentative.FLOOR_FREE


def test_a_record_that_carried_no_colour_floor_marks_no_seat_with_one():
    """`shortfalls.cell_floors` is `null` on a pass that ran without one, and every
    record before 2026-09-09 is such a pass. The mark has to be absent rather than
    guessed at, or a re-browsed old gallery would grow floor badges."""
    record = record_of(seat("k0", seated_for="general_pool"))
    record["shortfalls"]["cell_floors"] = None

    row = tentative.rows_of(record)[0]
    assert row["floor"] == tentative.FLOOR_FREE and row["floor_cells"] == []


def test_a_seat_with_no_dominant_colour_records_null_rather_than_a_guess():
    """A picture the codebook reads as neutral is dominant in nothing, and a
    record that invented a family for it would be a filter answering wrongly."""
    rows = tentative.rows_of(record_of(seat("k0", cells=[], families=[])))

    assert rows[0]["cell"] is None and rows[0]["hue_family"] is None
    assert tentative.counts_of(rows, "hue_family") == {"null": 1}


def test_the_seat_this_file_builds_is_the_seat_solve_actually_writes():
    """Every guard below reads a hand-built seat, so the hand-built shape has to be
    the real one. `solve._seated` is the only writer of a seat and the columns here
    are read straight off it — a field added there and not here would leave this
    file testing a record that no longer exists."""
    from fractal_wallpapers.curation import solve

    real = solve._seated(
        solve.Candidate(
            key="k0",
            location="place-of-k0",
            partition="mandelbrot",
            mode="direct_trap_multiply",
            group="map:viridis",
            kind="strange_render",
            cells=("dark_vivid_green",),
            families=("green",),
            score=0.9,
            p_ge3=0.95,
            picture="artifacts/p.jpg",
            mode_params={"opacity": 0.6},
        ),
        "general_pool",
        rank=0.5,
    )

    assert set(seat("k0")) == set(real), "the hand-built seat and the written one differ"
    assert real["mode_params"] == {"opacity": 0.6}, "the settings reach the record at all"


def test_a_seated_settings_cell_round_trips_through_the_spelling_a_roster_uses():
    """The column exists so a settings cell is visible in the record at all.

    Without it `direct_trap_multiply@opacity=0.6` and the bare mode are one row
    here and telling them apart needs a join to the ledger on `key`. The
    round-trip is the property that matters: whatever a leg named on its roster
    has to come back out of the record as the same pair."""
    rows = tentative.rows_of(
        record_of(
            seat("k0", mode="direct_trap_multiply", mode_params={"opacity": 0.6}),
            seat("k1"),
        )
    )

    held = {row["key"]: row for row in rows}
    assert held["k0"]["mode"] == "direct_trap_multiply", "the mode stays a catalogue name"
    assert held["k0"]["mode_params"] == {"opacity": 0.6}
    assert held["k1"]["mode_params"] == {}, "a bare seat is an empty cell, not a missing one"

    spelled = colorize.spelled(held["k0"]["mode"], held["k0"]["mode_params"])
    assert spelled == "direct_trap_multiply@opacity=0.6"
    assert colorize.roster_entry(spelled) == ("direct_trap_multiply", {"opacity": 0.6})


def test_a_seat_written_before_the_settings_column_existed_reads_as_bare():
    """Forward only: nothing tracked was rewritten when the column arrived, so a
    record from before it has to mean the same thing as a bare seat rather than
    raising or reading as `None`."""
    old = seat("k0")
    del old["mode_params"]

    rows = tentative.rows_of(record_of(old))

    assert rows[0]["mode_params"] == {}
    assert colorize.spelled(rows[0]["mode"], rows[0]["mode_params"]) == "smooth"


def test_the_centered_flag_is_joined_off_the_walk_ledgers_and_not_off_the_seat():
    """Nothing downstream of a walk carries the flag — not the embedding store,
    not the supply sidecar, not the candidate ledger — so it is joined at record
    time on the location key, which is the only place it survives."""
    rows = tentative.rows_of(record_of(seat("k0"), seat("k1")), centered=frozenset({"place-of-k1"}))

    assert [row["centered"] for row in rows] == [False, True]


def test_the_seat_order_is_the_solve_s_own_walk():
    """The order the leg seated in, which is what a reader comparing a record
    against the solve's log is looking at."""
    rows = tentative.rows_of(record_of(seat("k0"), seat("k1"), seat("k2")))

    assert [row["seat"] for row in rows] == [0, 1, 2]
    assert [row["key"] for row in rows] == ["k0", "k1", "k2"]


# --------------------------------------------------------------------------- #
# The record on disk.
# --------------------------------------------------------------------------- #
def test_a_recorded_gallery_holds_its_rows_its_manifest_and_the_shortfall(store):
    """The manifest is what says whether two records are comparable, and the
    shortfall is a finding rather than an error: a record cut to what filled
    would be a record that hides the one number this size was solved to read."""
    directory = tentative.write(record_of(seat("k0"), seat("k1"), n=10), log=quiet)
    stamp = directory.name

    manifest = tentative.read_manifest(stamp)
    assert manifest["seats"] == {"asked": 10, "filled": 2, "shortfall": 8, "recorded": 2}
    assert manifest["counts"]["mode"] == {"smooth": 2}
    assert tentative.stamps() == [stamp]
    assert len(tentative.read_rows(stamp)) == 2


def test_the_manifest_names_the_diversity_rule_the_solve_ran(store):
    """`config` carries no `rules` block, so the rule that decided two seats were
    different enough lived only on the solve record — which a published stamp does
    not carry. A themed record could not say which rule chose it, and two
    galleries chosen under different rules are not comparable."""
    record = record_of(seat("k0"), n=10)
    record["rules"] = {
        "diversity": {"rule": "geometry", "threshold": 0.3, "neighbours": 8},
    }
    stamp = tentative.write(record, stamp="20260911T000000Z", log=quiet).name

    held = tentative.read_manifest(stamp)["solve"]
    assert held["diversity"] == {"rule": "geometry", "threshold": 0.3, "neighbours": 8}
    assert "rules.State.record" in held["diversity_is"]
    # Carried WHOLE off the record rather than restated, which is the same rule
    # `config` is carried under: a second spelling is a second thing to keep true.
    # Asked of `manifest_of` directly, before the JSON round trip can hide it.
    built = tentative.manifest_of(record, rows=[], stamp="x")
    assert built["solve"]["diversity"] is record["rules"]["diversity"]


def test_a_manifest_says_null_diversity_out_loud_rather_than_going_quiet(store):
    """A pass that ran with no diversity rule at all is a real answer, and the
    `fine_bar` lesson is that a missing field puts a reader back on the date."""
    written = tentative.write(record_of(seat("k0")), stamp="20260911T000001Z", log=quiet)
    silent = tentative.read_manifest(written.name)
    assert silent["solve"]["diversity"] is None

    record = record_of(seat("k1"))
    record["rules"] = {"diversity": None}
    asked = tentative.read_manifest(
        tentative.write(record, stamp="20260911T000002Z", log=quiet).name
    )
    assert asked["solve"]["diversity"] is None


def test_a_stamp_is_written_once_and_never_over(store):
    """The IDs in a record are what a figure prompt names, so re-recording under
    a stamp somebody is already holding would move the aliases under a reader.
    A second folder is the cheap answer; a rewritten one has no answer."""
    tentative.write(record_of(seat("k0")), stamp="20260902T000000Z", log=quiet)

    with pytest.raises(tentative.TentativeRefused, match="already a recorded gallery"):
        tentative.write(record_of(seat("k1")), stamp="20260902T000000Z", log=quiet)

    assert [row["key"] for row in tentative.read_rows("20260902T000000Z")] == ["k0"]


def test_a_stamp_with_no_rows_is_not_a_gallery(store):
    """A folder claimed by a record that died before writing is not something a
    resolver may default to — it would answer nothing for every ID that exists."""
    (store / "curation" / "tentative" / "20260902T000000Z").mkdir(parents=True)

    assert tentative.stamps() == []
    with pytest.raises(tentative.TentativeRefused, match="no tentative gallery"):
        tentative.latest()


# --------------------------------------------------------------------------- #
# The resolver.
# --------------------------------------------------------------------------- #
def test_every_id_a_record_names_resolves_by_key_and_by_alias(store, isolated):  # noqa: F811
    """**The claim the store exists for.** A figure prompt names an alias and has
    to get back a location and a recipe, and the recipe comes from the candidate
    ledger rather than from the seat row: a seat is what a rule reads, and a
    render reads a recipe."""
    source = decision()
    recipe = recipes.of_decision(source)
    candidate_ledger.write(
        [
            candidate_ledger.row(
                recipe=recipe,
                key=key,
                source={**source, "_store": candidate_ledger.FROM_GALLERY},
                picture=None,
            )
            for key in ("k0", "k1")
        ]
    )
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)
    rows = tentative.read_rows()

    for row in rows:
        for name in (row["key"], row["alias"]):
            (answer,) = tentative.resolve([name])
            assert answer["found"], f"{name} does not resolve"
            assert answer["row"]["key"] == row["key"]
            assert answer["recipe"] == recipe.record()
            assert answer["picture"] == row["picture"]


def test_a_comma_list_answers_for_the_names_it_knows_and_says_so_for_the_rest(store):
    """A list of ten aliases with one typo in it should answer for the nine. The
    caller decides what a miss is worth; refusing the whole call does not."""
    recipes_beside(tentative.write(record_of(seat("k0"), seat("k1")), log=quiet).name, "k0", "k1")

    answers = tentative.resolve(["k0", "not-an-id", "k1"])

    assert [held["name"] for held in answers] == ["k0", "not-an-id", "k1"]
    assert [held["found"] for held in answers] == [True, False, True]
    assert answers[1]["row"] is None and answers[1]["recipe"] is None


def test_the_resolver_says_whether_the_picture_is_actually_on_this_disk(store):
    """The one thing a stale record cannot tell a reader from its rows alone, and
    the exact failure the retention protection exists to prevent."""
    here = store / "curation" / "depth" / "a_leg" / "pictures"
    here.mkdir(parents=True)
    (here / "k0.jpg").write_bytes(b"0" * 8)
    recipes_beside(tentative.write(record_of(seat("k0"), seat("k1")), log=quiet).name, "k0", "k1")

    answers = {held["name"]: held for held in tentative.resolve(["k0", "k1"])}

    assert answers["k0"]["picture_on_disk"] is True
    assert answers["k1"]["picture_on_disk"] is False


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def test_the_page_is_self_contained_and_opens_from_the_file_system(store):
    """No server, no build step, no CDN. The rows are embedded rather than
    fetched because a `fetch` of a sibling file is refused under `file://`, and
    every reference the page makes is a relative path to a JPEG already here."""
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert "http://" not in page and "https://" not in page
    assert "<script src" not in page and "fetch(" not in page
    assert '<link rel="stylesheet"' not in page


def test_the_page_opens_in_the_presentation_order_and_says_what_it_ordered_on(store):
    """The seats carry a derived position and the sort control opens on it.

    Both halves, because either alone passes for the wrong reason: a column nothing
    sorts by is dead weight, and a default option with no column behind it sorts by
    `undefined`. The basis is on the page for the reason [`page_order.basis`] gives —
    the same rows order two ways depending on whether this machine holds the store,
    and under this file's `no_embedding_store` it is always the clone's answer.
    """
    tentative.write(record_of(seat("k0"), seat("k1"), seat("k2")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")
    embedded = json.loads(page.split("const ROWS = ", 1)[1].split(";\n", 1)[0])

    assert sorted(row["order"] for row in embedded) == [0, 1, 2]
    # The FIRST option is what the page opens on, and it has to be this one.
    assert (
        page.split('<select id="sort">', 1)[1]
        .lstrip()
        .startswith('<option value="order">presentation order</option>')
    )
    assert f"presented on {page_order.ATTRIBUTES_ONLY}" in page


def test_the_presentation_order_is_a_column_on_the_PAGE_and_never_on_the_record(store):
    """The claim that makes this safe: the order changes no record, no identity and
    no digest. `gallery.jsonl` is what it was and the column lives on the embedded
    copy alone, so an existing record gets today's order on its next build and a
    published stamp's two tracked files do not move."""
    tentative.write(record_of(seat("k0"), seat("k1")), stamp="20260902T000000Z", log=quiet)
    rows_before = tentative.rows_path("20260902T000000Z").read_bytes()

    page = tentative.page("20260902T000000Z", log=quiet).read_text(encoding="utf-8")
    embedded = json.loads(page.split("const ROWS = ", 1)[1].split(";\n", 1)[0])

    assert tentative.rows_path("20260902T000000Z").read_bytes() == rows_before
    assert all("order" not in row for row in tentative.read_rows("20260902T000000Z"))
    assert all("order" in row for row in embedded)


def test_every_tile_names_its_picture_relatively_and_carries_the_full_id(store):
    """Relative so the folder can be copied or synced elsewhere and still open,
    and the full ID rather than the alias because clicking the alias copies the
    ID — a page that only held the short name could not."""
    tentative.write(record_of(seat("k0")), stamp="20260902T000000Z", log=quiet)

    page = tentative.page("20260902T000000Z", log=quiet).read_text(encoding="utf-8")
    embedded = json.loads(page.split("const ROWS = ", 1)[1].split(";\n", 1)[0])

    assert embedded[0]["key"] == "k0"
    assert embedded[0]["src"] == "../../depth/a_leg/pictures/k0.jpg"
    assert not embedded[0]["src"].startswith("/"), "an absolute path does not travel"


def test_a_page_written_elsewhere_resolves_its_thumbnails_from_where_it_LANDS(store):
    """`--out` is a parameter rather than a copy afterwards for exactly this: an
    `index.html` moved by hand points at nothing, because every reference in it is
    relative to the folder it was written in."""
    tentative.write(record_of(seat("k0")), stamp="20260902T000000Z", log=quiet)
    beside = tentative.page("20260902T000000Z", log=quiet)

    elsewhere = tentative.page("20260902T000000Z", out=store / "sheet" / "gallery.html", log=quiet)
    embedded = json.loads(
        elsewhere.read_text(encoding="utf-8").split("const ROWS = ", 1)[1].split(";\n", 1)[0]
    )

    assert elsewhere == store / "sheet" / "gallery.html"
    assert embedded[0]["src"] == "../curation/depth/a_leg/pictures/k0.jpg"
    assert beside.is_file(), "the record's own page is left where it is"
    assert "../../depth/" in beside.read_text(encoding="utf-8")


def test_the_page_marks_the_seats_the_colour_floor_bought_and_can_filter_on_them(store):
    """A badge and a facet, because the question is asked both ways: *which of
    these did the floor drag in* wants the mark on the tile, and *show me only
    those* wants the filter."""
    record = record_of(seat("k0", seated_for="cell_floor:dark_vivid_green"), seat("k1"))
    record["shortfalls"]["cell_floors"] = floors_of(dark_vivid_green=(20, 20))
    tentative.write(record, log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert '<fieldset id="f-floor"><legend>colour floor</legend></fieldset>' in page
    assert '"floor"]' in page or '"floor",' in page, "the facet list has to hold it"
    assert "floor seated this" in page and "floor holds this" in page
    assert '<option value="floor">group by colour floor</option>' in page


def test_a_tile_names_every_cell_it_charges_and_not_only_the_leading_one(store):
    """A seat charges 2.1 cells on average and the floor is stated per cell, so a
    tile showing one membership cannot be checked against a floor at all."""
    tentative.write(record_of(seat("k0")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert 'row.cells.join(" + ")' in page


def test_the_page_opens_a_picture_full_size_rather_than_selecting_it(store):
    """A tile is ~224px of a 640x360 candidate, so a look at a thousand seats that
    can only see tiles cannot judge any of them. The picture click OPENS; the
    checkbox beside the alias selects. They were one gesture while the tile was the
    only size there was, and a click that did both would put a stray ID in the tray
    on every look."""
    tentative.write(record_of(seat("k0")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert 'img.addEventListener("click", () => openAt(' in page
    assert 'box.addEventListener("change", pick)' in page
    assert 'event.key === "Escape"' in page, "the view has to close without a mouse"
    assert 'event.key === "ArrowRight"' in page, "stepping is what makes 1,000 scannable"


def test_the_page_groups_on_the_leading_cell_so_the_sections_partition_the_seats(store):
    """Grouping cuts the seats into sections once each, which needs the LEADING
    cell and not the dominance list the FILTERS read: a seat dominant in three
    cells would stand in three sections, the section counts would sum past the
    seat count, and the full-size view would step through it three times."""
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert '<option value="cell">group by colour cell</option>' in page
    assert '<option value="mode">group by mode</option>' in page
    assert "function groupOf(row, facet) {\n  const one = row[facet];" in page, (
        "grouping must read the single leading value, never PLURAL's list"
    )


def test_browse_takes_its_stamp_from_the_argument_a_reader_just_read(store, capsys):
    """`curate solve browse <stamp>` is how the record's own output spells it, so
    the positional has to BE the stamp. It was ignored for one afternoon and
    `--stamp` was the only spelling that worked, which is not an error a reader can
    see: the command succeeded and rebuilt the newest record's page instead."""
    tentative.write(record_of(seat("k0")), stamp="20260901T000000Z", log=quiet)
    tentative.write(record_of(seat("k1")), stamp="20260902T000000Z", log=quiet)

    args = cli.build_parser().parse_args(["curate", "solve", "browse", "20260901T000000Z"])
    assert args.handler is cli.curate_solve
    assert cli.curate_solve(args) == 0

    assert tentative.page_path("20260901T000000Z").is_file()
    assert not tentative.page_path("20260902T000000Z").is_file(), (
        "the newest record's page was written for a stamp the reader named"
    )
    assert "20260901T000000Z" in capsys.readouterr().out


def test_the_viewer_is_one_path_with_no_stamp_in_it(store, capsys):
    """The bookmark. A record's own page names the stamp it is of and the official
    record moves every checkpoint, so a page beside the rows is the wrong thing to
    bookmark and a path Matt retypes is the wrong thing to document. `--viewer` is
    the only spelling of it and `viewer_dir` is the only spelling of the place."""
    tentative.write(record_of(seat("k0")), stamp="20260901T000000Z", log=quiet)
    tentative.write(record_of(seat("k1")), stamp="20260902T000000Z", log=quiet)

    args = cli.build_parser().parse_args(["curate", "solve", "browse", "--viewer"])
    assert cli.curate_solve(args) == 0

    written = tentative.viewer_dir() / tentative.PAGE_NAME
    assert written.is_file()
    assert "20260901T000000Z" not in tentative.viewer_dir().parts
    # The NEWEST published record with no stamp named, which is what the bookmark
    # is for: it answers "the gallery" rather than "that gallery".
    assert "20260902T000000Z" in written.read_text(encoding="utf-8")
    assert "20260902T000000Z" in capsys.readouterr().out


def test_the_viewer_and_an_out_path_are_two_places_and_not_given_together(store, tmp_path):
    """Either would have to be ignored, and a page written where the reader did
    not ask for it is `browse`'s own two-stamps failure in another spelling."""
    tentative.write(record_of(seat("k0")), log=quiet)

    args = cli.build_parser().parse_args(
        ["curate", "solve", "browse", "--viewer", "--out", str(tmp_path / "elsewhere.html")]
    )

    assert cli.curate_solve(args) == 1
    assert not (tentative.viewer_dir() / tentative.PAGE_NAME).exists()


def test_the_viewer_is_not_inside_the_record_store(store):
    """A viewer under `tentative/` would be a folder among the stamped ones that
    `stamps()` has to know is not a record, and a stamp-shaped name is the only
    thing that store holds. It is a sibling instead."""
    assert tentative.viewer_dir().name == tentative.VIEWER_UNIT
    assert tentative.store_root() not in tentative.viewer_dir().parents
    assert tentative.viewer_dir().parent == tentative.store_root().parent


def test_two_different_stamps_are_a_refusal_rather_than_a_silent_choice(store):
    """One of the two would have to be ignored, and either choice is a page the
    reader did not ask for."""
    tentative.write(record_of(seat("k0")), stamp="20260901T000000Z", log=quiet)

    args = cli.build_parser().parse_args(
        ["curate", "solve", "browse", "20260901T000000Z", "--stamp", "20260902T000000Z"]
    )

    assert cli.curate_solve(args) == 1


def test_resolving_a_name_the_record_does_not_hold_is_a_non_zero_exit(store):
    """The answer is still printed for every name that resolved — a list with one
    typo answers for the rest — and the status is what a script reads."""
    tentative.write(record_of(seat("k0")), log=quiet)

    args = cli.build_parser().parse_args(["curate", "solve", "resolve", "k0,not-an-id"])

    assert cli.curate_solve(args) == 1


# --------------------------------------------------------------------------- #
# The protection. This is the one that keeps the IDs resolvable.
# --------------------------------------------------------------------------- #
def test_retention_keeps_a_recorded_seat_the_rank_would_have_dropped(
    isolated,  # noqa: F811
    tentative_store,
    monkeypatch,
):
    """**The guard the whole store rests on.** A seat wins its place on the
    gallery's objective — over a view, against the colour rules — and none of
    that is being in the top K of its own (location, mode) pair, so the rank
    drops these routinely. Without the protection an alias would stop resolving
    and its picture would already be gone, and nothing would say so.

    Both rows are unscored here, so [`retention.decide`] ranks them last within
    the pair and breaks the tie on the key: at K=1 `k1` is the one dropped, which
    is what makes it the row worth recording.

    **One prune and not a before-and-after**, because `saved_by_a_protection` is
    already the counterfactual: it counts the protected keys whose *rank verdict*
    was not `RANKED`, so a 1 there is this record's seat being dropped by the rank
    and kept by the protection, in one number. A second dry run would pay the
    supply sidecar and the served-location index again for a claim already made.

    The record is written at a named stamp and that stamp is put on the keep list,
    because since 2026-09-13 the keep list is the whole of what `protected_keys`
    reads — a record merely existing protects nothing.
    """
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ("20260101T000000Z",))
    rows = []
    for key in ("k0", "k1"):
        source = decision(candidate=key)
        rows.append(
            candidate_ledger.row(
                recipe=recipes.of_decision(source),
                key=key,
                source={**source, "_store": candidate_ledger.FROM_GALLERY},
                picture=f"artifacts/curation/depth/a_leg/pictures/{key}.jpg",
            )
        )
    candidate_ledger.write(rows)
    tentative.write(record_of(seat("k1")), stamp="20260101T000000Z", log=quiet)
    kept = candidate_ledger.prune(keep=1, apply=True, log=quiet)

    assert kept["rows_kept"] == 2, "a recorded seat the rank dropped was not protected"
    assert kept["kept_because"][candidate_ledger.RETAINED_TENTATIVE] == 1
    assert kept["saved_by_a_protection"][candidate_ledger.RETAINED_TENTATIVE] == 1, (
        "the rank did not drop this row, so the protection was never the reason it stayed"
    )
    assert kept["pictures"] == {**kept["pictures"], "asked": 0, "deleted": 0}
    assert {row["key"] for row in candidate_ledger.read()} == {"k0", "k1"}


@pytest.mark.slow
def test_the_protection_reads_every_kept_record_and_not_only_the_newest(
    tentative_store, monkeypatch
):
    """An older kept record's IDs are exactly the ones somebody is still holding. A
    protection that read only the latest would sweep last week's page silently."""
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ("20260901T000000Z", "20260902T000000Z"))
    tentative.write(record_of(seat("k0")), stamp="20260901T000000Z", log=quiet)
    tentative.write(record_of(seat("k1")), stamp="20260902T000000Z", log=quiet)

    assert tentative.protected_keys() == {"k0", "k1"}


def test_a_record_the_protection_cannot_parse_does_not_stop_a_prune(tentative_store, monkeypatch):
    """`prune` is the only thing in this project that removes a candidate, and it
    runs inside every merge. A browser's store must not be able to stop it.

    The unparseable record is on the keep list, or this would pass by never
    reading the folder at all — which is a different claim than the one here.
    """
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ("20260902T000000Z",))
    directory = tentative_store / "20260902T000000Z"
    directory.mkdir(parents=True)
    (directory / tentative.ROWS_NAME).write_text("{not json\n", encoding="utf-8")

    assert tentative.protected_keys() == set()


def test_the_protection_is_wired_into_the_prune_and_not_only_declared():
    """The reason and the set that fills it are in two places, and a class named
    in `RETAINED_REASONS` that nothing fills would keep exactly nothing while
    reading, on the record, as a protection that ran."""
    import inspect

    assert candidate_ledger.RETAINED_TENTATIVE in candidate_ledger.RETAINED_REASONS
    body = inspect.getsource(candidate_ledger._prune_protections)
    assert "tentative.protected_keys()" in body
    assert "RETAINED_TENTATIVE:" in body


# --------------------------------------------------------------------------- #
# Publication: which records a clone gets, and what an unstamped read means.
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parents[1]

#: How `.gitignore` spells one published stamp.
NEGATION = "!artifacts/curation/tentative/"


def negated_stamps() -> list[str]:
    """The stamps `.gitignore` un-ignores, in the order it names them."""
    held = []
    for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith(NEGATION):
            continue
        rest = line[len(NEGATION) :]
        if rest.endswith("/") and "*" not in rest:
            held.append(rest.rstrip("/"))
    return held


def test_the_published_list_and_the_gitignore_negations_are_one_list():
    """Two spellings of Matt's ruling, and nothing but this holds them together.

    Git cannot read a Python tuple and `tentative` must not shell out to git to
    answer what an unstamped read means, so the list is written twice. Drift has
    a silent failure on each side: a stamp in `PUBLISHED` that git ignores is an
    ID `latest()` hands out and a clone cannot resolve, and a stamp git tracks
    that `PUBLISHED` omits is a record shipped to everybody that no unstamped
    read will ever reach.
    """
    assert negated_stamps() == list(tentative.PUBLISHED)


def test_every_published_stamp_is_actually_in_the_tree():
    """A published stamp is tracked, so a clone has its two text files. One named
    in both lists and absent from the tree is an ID that resolves nowhere."""
    for stamp in tentative.PUBLISHED:
        directory = REPO_ROOT / "artifacts" / "curation" / "tentative" / stamp
        for name in (tentative.ROWS_NAME, tentative.MANIFEST_NAME):
            assert (directory / name).is_file(), f"{stamp}/{name} is published and not here"


def tracked(pattern: str) -> list[str]:
    """`git ls-files` on one pathspec, from the repository root."""
    import subprocess

    done = subprocess.run(
        ["git", "ls-files", "--", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in done.stdout.splitlines() if line.strip()]


def test_the_page_is_a_derivation_and_no_stamp_tracks_one():
    """Matt's ruling of 2026-09-05: a record is `gallery.jsonl` plus the manifest,
    and `index.html` is a browse view `curate solve browse <stamp>` writes from
    the rows. It was tracked per published stamp until then, which put 4.1 MB of
    derivation in the history against the rows' 2.5 MB.

    Both halves are asserted, because either alone passes for the wrong reason: a
    published stamp still tracks its rows, and NO stamp tracks a page. `.gitignore`
    and `tentative.PUBLISHED` cannot say the second on their own — an un-ignore
    stops nothing that git already has in the index, which is why the seven were
    removed from it by hand and why this guards the index and not the rules.
    """
    assert tracked("artifacts/curation/tentative/*/" + tentative.PAGE_NAME) == []
    rows = tracked("artifacts/curation/tentative/*/" + tentative.ROWS_NAME)
    assert sorted(Path(name).parent.name for name in rows) == sorted(tentative.PUBLISHED)


def test_the_page_is_written_from_the_two_tracked_files_alone(tentative_store):
    """The claim that makes the page droppable: a stamp holding nothing but the
    two TRACKED files can write it. That is what a clone has, and it is why
    `curate solve browse <stamp>` is the answer to an untracked `index.html`."""
    stamp = "20260905T000000Z"
    directory = tentative_store / stamp
    directory.mkdir(parents=True)
    (directory / tentative.ROWS_NAME).write_text(
        json.dumps({"key": "abcdef0123456789", "alias": "abcdef01", "picture": "a.jpg"}) + "\n",
        encoding="utf-8",
    )
    (directory / tentative.MANIFEST_NAME).write_text(
        json.dumps({"seats": {"asked": 1, "filled": 1}}), encoding="utf-8"
    )
    assert not (directory / tentative.PAGE_NAME).exists()

    written = tentative.page(stamp, log=lambda *_: None)

    assert written == directory / tentative.PAGE_NAME
    held = written.read_text(encoding="utf-8")
    assert "abcdef0123456789" in held and stamp in held


def recorded(directory: Path, stamp: str, key: str) -> None:
    """One stamp holding one row, which is all `stamps` asks of a gallery."""
    (directory / stamp).mkdir(parents=True)
    (directory / stamp / tentative.ROWS_NAME).write_text(
        json.dumps({"key": key}) + "\n", encoding="utf-8"
    )


def test_an_unstamped_read_lands_on_the_newest_PUBLISHED_record(tentative_store, monkeypatch):
    """The ruling: recording a gallery does not publish it. An experimental
    record left in the store must not become the answer for every figure prompt,
    naming IDs that exist on one machine."""
    for stamp in ("20260101T000000Z", "20260202T000000Z", "20260303T000000Z"):
        recorded(tentative_store, stamp, stamp)
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z", "20260202T000000Z"))

    assert tentative.stamps()[-1] == "20260303T000000Z"
    assert tentative.latest() == "20260202T000000Z"
    assert tentative.published() == ["20260101T000000Z", "20260202T000000Z"]
    # The unpublished one is still READ, by naming it. That is the whole way it
    # is reached for as long as it exists — and since 2026-09-13 it exists only
    # until whatever it was recorded to measure has been measured.
    assert tentative.read_rows("20260303T000000Z") == [{"key": "20260303T000000Z"}]


def test_a_published_stamp_this_machine_does_not_hold_is_not_offered(tentative_store, monkeypatch):
    """`published` intersects with the store. A clone has every published stamp's
    text files, but a machine that has never solved holds no pictures for them —
    and `latest` answers a reader who is about to read one."""
    recorded(tentative_store, "20260101T000000Z", "k0")
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z", "20260909T000000Z"))

    assert tentative.published() == ["20260101T000000Z"]
    assert tentative.latest() == "20260101T000000Z"


def test_an_unpublished_record_is_named_in_the_refusal_rather_than_ignored(
    tentative_store, monkeypatch
):
    """A store holding only unpublished records refuses an unstamped read, and
    says which stamps are there — otherwise the reader is told nothing has been
    recorded while looking at a folder full of records."""
    recorded(tentative_store, "20260303T000000Z", "k0")
    monkeypatch.setattr(tentative, "PUBLISHED", ())

    with pytest.raises(tentative.TentativeRefused, match="20260303T000000Z"):
        tentative.latest()


def test_the_protection_keeps_an_unpublished_record_the_keep_list_names(
    tentative_store, monkeypatch
):
    """**Publication, durability and retention are three questions**, Matt's
    ruling, and this is the third one answered on its own. An unpublished record
    is protected when `KEPT_UNPUBLISHED` names it and not otherwise — publication
    is not the input, but neither is the folder's mere existence."""
    recorded(tentative_store, "20260101T000000Z", "k0")
    recorded(tentative_store, "20260303T000000Z", "k1")
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z",))
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ("20260303T000000Z",))

    assert tentative.protected_keys() == {"k0", "k1"}


def test_a_record_off_the_keep_list_pins_nothing(tentative_store, monkeypatch):
    """**The 2026-09-13 reversal, stated as its own guard.** Before it, a solve
    record written to measure one number against held every seat it named against
    the prune for as long as the folder sat there — preservation conferred by an
    ephemeral artifact, which is the policy backwards and is why sweeping the
    store kept arriving as a recurring approval.

    `k1`'s record is readable by naming its stamp and votes on nothing.
    """
    recorded(tentative_store, "20260101T000000Z", "k0")
    recorded(tentative_store, "20260303T000000Z", "k1")
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z",))
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ())

    assert tentative.protected_keys() == {"k0"}
    assert tentative.kept() == ["20260101T000000Z"]
    assert "20260303T000000Z" in tentative.stamps(), "the record is still there to be read"
    assert [row["key"] for row in tentative.read_rows("20260303T000000Z")] == ["k1"]


def test_the_keep_list_is_published_plus_the_named_unpublished_and_holds_no_ghost(
    tentative_store, monkeypatch
):
    """`kept` is intersected with the store for the same reason `published` is: a
    caller of it wants records it can read, and a clone holds published text files
    for stamps whose pictures it has never rendered. A name on either list that
    this machine does not hold is not an error and is not returned."""
    recorded(tentative_store, "20260101T000000Z", "k0")
    recorded(tentative_store, "20260303T000000Z", "k1")
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z", "20261212T000000Z"))
    monkeypatch.setattr(tentative, "KEPT_UNPUBLISHED", ("20260303T000000Z", "20261111T000000Z"))

    assert tentative.kept() == ["20260101T000000Z", "20260303T000000Z"]


# --------------------------------------------------------------------------- #
# The full-resolution option.
# --------------------------------------------------------------------------- #
def a_full(store: Path, key: str) -> Path:
    """The release-geometry picture of one seat, where `fulls` keeps its own."""
    from fractal_wallpapers.curation import fulls

    picture = fulls.store_dir() / "pictures" / f"{key}.jpg"
    picture.parent.mkdir(parents=True, exist_ok=True)
    picture.write_bytes(b"not really a jpeg")
    return picture


def test_the_page_carries_the_release_geometry_picture_where_the_record_has_one(store):
    """Resolved at build time and never by the page: `file://` cannot look in a
    directory, so a seat with no full picture has to ARRIVE with an empty string."""
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)
    a_full(store, "k0")

    page = tentative.page(log=quiet).read_text(encoding="utf-8")
    rows = json.loads(page.split("const ROWS = ", 1)[1].split(";\n", 1)[0])
    embedded = {row["key"]: row for row in rows}

    assert embedded["k0"]["full"].endswith("k0.jpg")
    assert embedded["k1"]["full"] == "", "a seat with no full picture claimed one"
    assert "1 of 2 seats have a 1280x720ss2" in page


def test_the_grid_opens_on_the_candidate_and_the_toggle_swaps_it(store):
    """The small cut is the default because a thousand 1280x720 JPEGs is a page
    that does not open. The toggle is an UPGRADE where one exists and never a
    filter: a seat with no full picture keeps its candidate under it."""
    tentative.write(record_of(seat("k0")), log=quiet)
    a_full(store, "k0")

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert "let hires = false;" in page, "the page opens on the full cut"
    assert 'return (hires && row.full) ? row.full : (row.src || row.full || "");' in page
    assert "img.src = pictureOf(row);" in page
    assert 'document.getElementById("hires").addEventListener("change"' in page


def test_the_resolution_toggle_survives_clear_filters(store):
    """`clear filters` unchecks every box in the header, and this one is not a
    filter — swept by it, the control would go off on screen while the page went
    on loading full-resolution pictures underneath."""
    tentative.write(record_of(seat("k0")), log=quiet)

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert 'if (box.id !== "hires") box.checked = false;' in page


def test_the_full_size_view_always_takes_the_release_geometry_picture(store):
    """The header has promised "the full size" since this page existed and could
    only ever show the candidate blown up. The toggle governs the GRID."""
    tentative.write(record_of(seat("k0")), log=quiet)
    a_full(store, "k0")

    page = tentative.page(log=quiet).read_text(encoding="utf-8")

    assert 'view.querySelector("img").src = row.full || row.src || "";' in page


# --------------------------------------------------------------------------- #
# The recipe file: what makes a published record redrawable at all.
# --------------------------------------------------------------------------- #
def test_the_resolver_refuses_rather_than_answering_that_a_seat_has_no_recipe(store):
    """`"recipe": null` with exit 0 is the wrong answer and it was the answer.

    It says *this seat has no recipe*, which is a fact about a picture; the truth
    is *this machine has nothing to look one up in*, which is a missing store.
    Every seat of every record was made from a recipe, so the first is never true
    and the command said it anyway — and a figure prompt reading the JSON could
    not tell the two apart.
    """
    tentative.write(record_of(seat("k0")), log=quiet)

    with pytest.raises(tentative.TentativeRefused) as refusal:
        tentative.resolve(["k0"])

    said = str(refusal.value)
    assert tentative.RECIPES_NAME in said and "candidate ledger" in said
    assert "curate solve recipes" in said


def test_the_tracked_file_answers_and_says_it_was_the_one_that_did(store):
    """The half a clone has. It is preferred over the ledger because it is what
    travels — and because it is the record's own statement about its seats rather
    than a lookup in a store that has grown and pruned since."""
    stamp = tentative.write(record_of(seat("k0")), log=quiet).name
    written = recipes_beside(stamp, "k0")

    (answer,) = tentative.resolve(["k0"])

    assert answer["recipe"] == recipes.of_decision(decision()).record()
    assert answer["recipe_from"].endswith(tentative.RECIPES_NAME)
    assert written.is_file()


def test_read_recipes_names_the_command_when_a_record_has_no_file(store):
    stamp = tentative.write(record_of(seat("k0")), log=quiet).name

    with pytest.raises(tentative.TentativeRefused, match="curate solve recipes"):
        tentative.read_recipes(stamp)


def test_every_row_written_recomputes_its_own_key(store, isolated):  # noqa: F811
    """A recipe file whose keys do not recompute names DIFFERENT pictures under
    the record's own names, which is worse than the record having no recipe file
    at all. So `build_recipes` checks each row through `recipes.of_record` and
    `recipes.key_of` before writing it, and refuses the ones that fail rather
    than writing them and counting them as covered."""
    source = decision()
    recipe = recipes.of_decision(source)
    key = recipes.key_of(recipe)
    candidate_ledger.write(
        [
            candidate_ledger.row(
                recipe=recipe,
                key=key,
                source={**source, "_store": candidate_ledger.FROM_GALLERY},
                picture=None,
            )
        ]
    )
    stamp = tentative.write(record_of(seat(key)), log=quiet).name

    rows, readout = tentative.build_recipes(stamp)

    assert readout["written"] == readout["seats"] == 1
    assert not readout["refused"] and not readout["not_in_the_ledger"]
    assert recipes.key_of(recipes.of_record(rows[0]["recipe"])) == rows[0]["key"] == key


def test_a_seat_the_ledger_does_not_hold_is_reported_and_not_skipped(store, isolated):  # noqa: F811
    """The one gap the file cannot close. A count that quietly omitted it would
    read as full coverage of a record that has none."""
    candidate_ledger.write([])
    stamp = tentative.write(record_of(seat("nowhere")), log=quiet).name

    _rows, readout = tentative.build_recipes(stamp)

    assert readout["not_in_the_ledger"] == ["nowhere"]
    assert readout["written"] == 0


# --------------------------------------------------------------------------- #
# The published record, against the file this repository actually tracks.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_the_published_record_can_be_redrawn_from_tracked_data_alone():
    """★ The claim the whole file exists to make, asserted on the real one.

    `20260914T171846Z` is the official n=1000 record, and before 2026-09-14 994
    of its 1,000 seats could not be drawn from anything a clone has: the key is a
    one-way digest, the recipe behind it lives in the untracked ledger, and 529
    seats carry a continuous `palette.phase` so recovery by search is out. This
    reads the two TRACKED files and nothing else.

    Slow because it recomputes all thousand keys — `of_record` then `key_of`,
    which is a JSON round trip and a sha256 per seat — and that is the assertion
    rather than a way of reaching it. A sample would leave the file's coverage
    unasserted, which is the one thing about it worth asserting.
    """
    stamp = "20260914T171846Z"
    assert stamp in tentative.PUBLISHED
    seats = [str(row["key"]) for row in tentative.read_rows(stamp)]
    held = tentative.read_recipes(stamp)

    assert len(seats) == 1000
    missing = [key for key in seats if key not in held]
    assert not missing, f"{len(missing)} published seat(s) carry no recipe"
    for key in seats:
        assert recipes.key_of(recipes.of_record(held[key])) == key


def test_the_tracked_recipe_file_stays_under_the_history_size_rule():
    """0.68 MiB against `test_history_purity.MAX_TRACKED_BYTES`, and smaller than
    the `gallery.jsonl` beside it. That margin is why this is a tracked file and
    not a release asset — and it is per stamp, so it is worth knowing where it
    sits before a second record is published."""
    stamp = "20260914T171846Z"
    written = tentative.recipes_path(stamp).stat().st_size
    assert written < (1 << 20)
    assert written < 2 * tentative.rows_path(stamp).stat().st_size
