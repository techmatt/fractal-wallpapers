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
from fractal_wallpapers.curation import candidate_ledger, colorize, recipes, tentative


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
        "pool": {"reachable_locations": 99, "refused": {}},
        "shortfalls": {"seats": {"asked": n, "filled": len(seats)}},
        "taken_at": "2026-09-02T00:00:00Z",
        "seconds": 1.0,
    }


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


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
    """
    monkeypatch.setattr(tentative, "store_root", lambda: tmp_path / "tentative")
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
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)

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
    tentative.write(record_of(seat("k0"), seat("k1")), log=quiet)

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
    """
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
    tentative.write(record_of(seat("k1")), log=quiet)
    kept = candidate_ledger.prune(keep=1, apply=True, log=quiet)

    assert kept["rows_kept"] == 2, "a recorded seat the rank dropped was not protected"
    assert kept["kept_because"][candidate_ledger.RETAINED_TENTATIVE] == 1
    assert kept["saved_by_a_protection"][candidate_ledger.RETAINED_TENTATIVE] == 1, (
        "the rank did not drop this row, so the protection was never the reason it stayed"
    )
    assert kept["pictures"] == {**kept["pictures"], "asked": 0, "deleted": 0}
    assert {row["key"] for row in candidate_ledger.read()} == {"k0", "k1"}


def test_the_protection_reads_every_record_and_not_only_the_newest(tentative_store):
    """An older record's IDs are exactly the ones somebody is still holding. A
    protection that read only the latest would sweep last week's page silently."""
    tentative.write(record_of(seat("k0")), stamp="20260901T000000Z", log=quiet)
    tentative.write(record_of(seat("k1")), stamp="20260902T000000Z", log=quiet)

    assert tentative.protected_keys() == {"k0", "k1"}


def test_a_record_the_protection_cannot_parse_does_not_stop_a_prune(tentative_store):
    """`prune` is the only thing in this project that removes a candidate, and it
    runs inside every merge. A browser's store must not be able to stop it."""
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
    # is reached, and it is kept rather than swept.
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


def test_the_protection_keeps_an_unpublished_record_too(tentative_store, monkeypatch):
    """**Publication and durability are different questions**, Matt's ruling. An
    unpublished record is kept: deleting it is the only thing that releases its
    seats, so `protected_keys` sweeps the whole store and never `PUBLISHED`."""
    recorded(tentative_store, "20260101T000000Z", "k0")
    recorded(tentative_store, "20260303T000000Z", "k1")
    monkeypatch.setattr(tentative, "PUBLISHED", ("20260101T000000Z",))

    assert tentative.protected_keys() == {"k0", "k1"}
