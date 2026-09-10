"""The voting kit: what a friend receives, and where its pictures came from.

Three claims, and the third is the one that needed a test written for it.

**The folder is complete.** Two JPEGs per seat, a page, a paragraph, a zip — a
kit missing any of them is a kit somebody cannot open or cannot send back.

**The page carries the join.** The seat list is embedded, it parses, and it is
the record's own keys in the record's own order, because a filename carries the
seat's *position* and the export carries the *recipe key* — an export whose keys
did not come from the record would be a label file that joins to nothing.

**The thumbnails came from the full renders.** The stored 640x360 candidate is
the obvious thing to downscale and it is the wrong picture: another size, another
autolevel curve. So the fixture's rows name candidate pictures that **do not
exist on this disk at all**, and the full render carries a two-tone pattern the
thumbnail is then checked for. A kit built off the candidates could not be built
here, and one built off the wrong half of the render would not carry the pattern.

Nothing here renders. [`votes.render_fulls`] is the seam and it is replaced with
a stub that writes a picture and calls the same `arrived` callback in the same
place, so the encode, the downscale, the page and the zip are all exercised.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from fractal_wallpapers.curation import tentative, votes

#: Three seats, so `--limit 2` is a real cut rather than the whole record.
KEYS = ("aaaa0000bbbb1111", "cccc2222dddd3333", "eeee4444ffff5555")

#: One mode each, and the first two differ so that a `--limit 2` cut still holds
#: two modes — a per-mode supersample override has to be a real split inside the
#: two-seat kit every other test here builds. The third is a mode the cut never
#: reaches, which is how an override that fires on nothing is checked.
MODES = ("smooth", "smooth_mean_angle", "threads")

#: What the stub renders: the left half one colour and the right half another, at
#: the frame a kit ships. A downscale of this keeps both halves; a crop, a
#: candidate, or a picture built from anything else does not.
LEFT, RIGHT = (200, 30, 40), (30, 60, 200)


@pytest.fixture
def store(tmp_path, monkeypatch):
    """The regenerable tree in `tmp_path`, and a synthetic record inside it.

    The tier redirect and not a patch of `tentative.gallery_dir`, for
    `tests/test_tentative`'s reason: one accessor moved is a path that reads past
    the redirect into this machine's real records.
    """
    from fractal_wallpapers import paths

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir()
    monkeypatch.setattr(tentative, "published", tentative.stamps)
    stamp = "20260101T000000Z"
    directory = tentative.gallery_dir(stamp)
    directory.mkdir(parents=True)
    rows = [
        {
            "schema": 1,
            "seat": index,
            "key": key,
            "alias": key[:8],
            "mode": MODES[index],
            "mode_params": {},
            "partition": "mandelbrot",
            # A path under the redirected tree that nothing ever writes: a kit
            # that reached for a candidate would fail here rather than quietly
            # ship the wrong picture.
            "picture": f"artifacts/curation/depth/nowhere/pictures/{key}.jpg",
        }
        for index, key in enumerate(KEYS)
    ]
    tentative.rows_path(stamp).write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    return stamp


@pytest.fixture
def stub_renders(monkeypatch):
    """[`votes.render_fulls`] without an engine, calling `arrived` where it does.

    Yields the list of legs it was driven through — one entry per call, carrying
    the regime and the keys handed to it — because a per-mode supersample makes
    the *number* of render passes and their contents part of what a kit is.
    """
    from PIL import Image

    legs: list[dict] = []

    def render_fulls(jobs, staging, regime, workers, arrived, log=print):
        legs.append({"regime": regime.spelled, "keys": [job["key"] for job in jobs]})
        staging.mkdir(parents=True, exist_ok=True)
        for job in jobs:
            picture = Image.new("RGB", votes.FRAME, LEFT)
            picture.paste(
                Image.new("RGB", (votes.FRAME[0] // 2, votes.FRAME[1]), RIGHT),
                (votes.FRAME[0] // 2, 0),
            )
            png = staging / f"{job['key']}.png"
            picture.save(png, compress_level=1)
            arrived(job, png)
        return {"regime": regime.spelled, "planned": len(jobs), "made": len(jobs), "failed": []}

    monkeypatch.setattr(votes, "render_fulls", render_fulls)
    return legs


def built(tmp_path, stamp, **over) -> dict:
    """A two-seat kit in `tmp_path`, with `over` applied to the build."""
    return votes.build(stamp=stamp, out=tmp_path / "kit", limit=2, log=lambda _line: None, **over)


def seat_list(directory: Path) -> list[dict]:
    """The seats the page embeds, read back the way an ingest would have to."""
    page = (directory / votes.PAGE_NAME).read_text(encoding="utf-8")
    found = re.search(r"^const SEATS = (\[.*\]);$", page, re.MULTILINE)
    assert found, "the page does not embed a seat list"
    return json.loads(found.group(1))


def test_a_kit_is_a_folder_a_friend_can_open_and_a_zip_to_send_it_in(
    tmp_path, store, stub_renders
) -> None:
    manifest = built(tmp_path, store)
    kit = tmp_path / "kit"
    # `manifest.json` travels with the kit and the leg's own numbers do not: a
    # folder that does not carry its master seed and its offsets cannot have its
    # decks reproduced from what a friend was sent, and `build` reads its seed
    # back out of it so a rebuild does not rotate anybody's remaining pages.
    assert sorted(path.name for path in kit.iterdir()) == sorted(
        [votes.PAGE_NAME, votes.READ_ME, votes.MANIFEST_NAME, votes.FULLS, votes.THUMBS]
    )
    # No `orders/` here: nobody was named, so there is no deck to write down
    # before somebody types a name into the un-named kit's box.
    assert not (kit / votes.ORDERS).exists()
    assert sorted(path.name for path in (kit / votes.FULLS).iterdir()) == [
        "s0000.jpg",
        "s0001.jpg",
    ]
    assert sorted(path.name for path in (kit / votes.THUMBS).iterdir()) == [
        "s0000.jpg",
        "s0001.jpg",
    ]
    # The staging tree is not left behind, and it is not in the zip either.
    assert not (kit / votes.STAGING).exists()
    bundle = Path(manifest["zip"])
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as held:
        names = held.namelist()
    assert f"kit/{votes.PAGE_NAME}" in names
    assert f"kit/{votes.FULLS}/s0000.jpg" in names
    assert not [name for name in names if votes.STAGING in name]


def test_the_page_embeds_the_records_own_keys_in_the_records_own_order(
    tmp_path, store, stub_renders
) -> None:
    """The filename is a position and the export is a recipe key, so the page is
    the only thing that joins the two. A page carrying anything else is a label
    file nothing can ingest."""
    built(tmp_path, store)
    assert [seat["key"] for seat in seat_list(tmp_path / "kit")] == list(KEYS[:2])


def test_a_thumbnail_is_a_downscale_of_the_full_render_and_never_of_the_candidate(
    tmp_path, store, stub_renders
) -> None:
    """The dimensions say it is not the candidate; the pattern says it is not a
    crop, a half, or the other seat's picture."""
    from PIL import Image

    built(tmp_path, store)
    kit = tmp_path / "kit"
    for name in ("s0000.jpg", "s0001.jpg"):
        with Image.open(kit / votes.FULLS / name) as full:
            assert full.size == votes.FRAME
        with Image.open(kit / votes.THUMBS / name) as thumb:
            assert thumb.size == (votes.THUMB_WIDTH, votes.THUMB_WIDTH * 9 // 16)
            left = thumb.convert("RGB").getpixel((thumb.width // 4, thumb.height // 2))
            right = thumb.convert("RGB").getpixel((3 * thumb.width // 4, thumb.height // 2))
        # JPEG at the shipped quality, so this is "much nearer than the other
        # half" rather than an equality on bytes.
        assert abs(left[0] - LEFT[0]) < 25 and abs(left[2] - LEFT[2]) < 25
        assert abs(right[2] - RIGHT[2]) < 25 and abs(right[0] - RIGHT[0]) < 25


def test_the_kit_names_its_encoding_and_the_frame_it_was_rendered_at(
    tmp_path, store, stub_renders
) -> None:
    """A kit that did not say would be a folder of JPEGs nobody could reproduce."""
    manifest = built(tmp_path, store, quality=85, chroma="444", supersample=4)
    assert manifest["encoding"] == {
        "quality": 85,
        "chroma": "444",
        "regime": "2560x1440ss4",
        "regime_for": {},
        "seats_at": {"ss4": 2},
    }
    assert manifest["record"] == store
    assert manifest["viewer"] == votes.VIEWER
    assert manifest["seats"] == 2


def test_a_seat_already_encoded_is_not_rendered_again(tmp_path, store, stub_renders) -> None:
    """The resume unit is the seat's two JPEGs and not the staging PNG, which is
    deleted as it goes — a thousand of those is ten gigabytes."""
    built(tmp_path, store)
    again = built(tmp_path, store)
    assert again["render"]["planned"] == 0


def test_a_chroma_nothing_ships_is_refused_rather_than_passed_to_pillow(tmp_path, store) -> None:
    """Pillow takes an integer here and would take a wrong one silently."""
    with pytest.raises(votes.VotesRefused):
        votes.build(stamp=store, out=tmp_path / "kit", chroma="422", log=lambda _line: None)


# --------------------------------------------------------------------------- #
# The per-mode supersample.
# --------------------------------------------------------------------------- #
def test_a_per_mode_supersample_splits_the_leg_and_renders_the_cheap_pass_first(
    tmp_path, store, stub_renders
) -> None:
    """One render pass per distinct supersample and not one overall, cheapest
    first — the whole point of the override is that most of a kit is cheap, so
    the fulls a person can look at have to start landing before the fine pass."""
    built(tmp_path, store, supersample=2, supersample_for={"smooth_mean_angle": 4})
    assert [leg["regime"] for leg in stub_renders] == ["2560x1440ss2", "2560x1440ss4"]
    assert [leg["keys"] for leg in stub_renders] == [[KEYS[0]], [KEYS[1]]]


def test_the_page_records_which_supersample_each_seat_was_rendered_at(
    tmp_path, store, stub_renders
) -> None:
    """In the seat list and never in the filename: the filename carries the
    position and nothing a friend can sort by. A kit whose seats were made at two
    supersamples and does not say which is which is un-reproducible at the seat."""
    built(tmp_path, store, supersample=2, supersample_for={"smooth_mean_angle": 4})
    assert seat_list(tmp_path / "kit") == [
        {"key": KEYS[0], "ss": 2},
        {"key": KEYS[1], "ss": 4},
    ]
    assert not [path for path in (tmp_path / "kit" / votes.FULLS).iterdir() if "ss" in path.name]


def test_the_manifest_says_what_was_overridden_and_what_that_came_to(
    tmp_path, store, stub_renders
) -> None:
    """`regime_for` is what was asked and `seats_at` is what the record's own
    modes turned it into — an override naming a mode this cut does not hold is
    legal, and the two blocks together are how it shows up as having fired on
    nothing."""
    manifest = built(
        tmp_path,
        store,
        supersample=2,
        supersample_for={"smooth_mean_angle": 4, "threads": 4},
    )
    assert manifest["encoding"]["regime"] == "2560x1440ss2"
    assert manifest["encoding"]["regime_for"] == {
        "smooth_mean_angle": "2560x1440ss4",
        "threads": "2560x1440ss4",
    }
    # `threads` is the third seat and `--limit 2` never reaches it.
    assert manifest["encoding"]["seats_at"] == {"ss2": 1, "ss4": 1}
    assert [leg["regime"] for leg in manifest["render"]["legs"]] == [
        "2560x1440ss2",
        "2560x1440ss4",
    ]
    assert manifest["render"]["planned"] == 2 and manifest["render"]["made"] == 2


def test_an_override_that_names_no_mode_of_this_record_is_not_an_error(
    tmp_path, store, stub_renders
) -> None:
    """A cut holds whatever modes its first N seats carry, so a mode missing from
    one cut is the ordinary case. The kit is the unsplit one."""
    built(tmp_path, store, supersample=2, supersample_for={"itinerary": 4})
    assert [leg["regime"] for leg in stub_renders] == ["2560x1440ss2"]


@pytest.mark.parametrize("text", ["smooth_mean_angle", "smooth_mean_angle=", "=4", "x=four"])
def test_a_supersample_override_that_is_not_one_is_refused_at_the_flag(text) -> None:
    """Before anything renders: a misspelt override is one that can never fire,
    and a twenty-hour leg would discover it at the end."""
    with pytest.raises(votes.VotesRefused):
        votes.parse_supersample_for(text)


@pytest.mark.parametrize("supersample", votes.SUPERSAMPLES)
def test_every_supersample_the_kit_takes_is_one_an_override_can_name(supersample) -> None:
    """2 and 4 are the priced pair the default's argument is a comparison
    between; 1 is the debugging cell, minutes rather than hours, for driving the
    viewer on a kit nobody is sent."""
    assert votes.parse_supersample_for(f"smooth_mean_angle={supersample}") == (
        "smooth_mean_angle",
        supersample,
    )


def test_a_supersample_the_kit_does_not_take_is_refused() -> None:
    """3 is a cell of the pilot's grid nobody has looked at, and a leg is not the
    place to discover that."""
    with pytest.raises(votes.VotesRefused):
        votes.parse_supersample_for("smooth_mean_angle=3")


def test_the_debugging_supersample_builds_a_whole_kit(tmp_path, store, stub_renders) -> None:
    """ss1 is a supersample like the others once it is past the flag: one pass,
    the frame unchanged, and the regime on the manifest and in the seat list, so
    a kit built to be driven still says what made it."""
    manifest = built(tmp_path, store, supersample=1)
    assert [leg["regime"] for leg in stub_renders] == ["2560x1440ss1"]
    assert manifest["encoding"]["regime"] == "2560x1440ss1"
    assert manifest["encoding"]["seats_at"] == {"ss1": 2}
    assert seat_list(tmp_path / "kit") == [{"key": KEYS[0], "ss": 1}, {"key": KEYS[1], "ss": 1}]


# --------------------------------------------------------------------------- #
# The three keys.
# --------------------------------------------------------------------------- #
def test_the_page_binds_one_two_and_three_to_clear_up_and_star(
    tmp_path, store, stub_renders
) -> None:
    """Matt's ruling of 2026-09-05: 1 clears, 2 is the thumbs-up, 3 is the star.
    The VOTE values stay 1 and 2, which is what the export carries and what an
    ingest joins on — shifting those to make room for a "no" would invalidate
    every label file already exported against a record.

    A key SETS and a button TOGGLES, and the page has to keep the two apart:
    a key that toggled would make 2 mean "like" on one picture and "un-like" on
    the next."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert 'const BY_KEY = new Map([["1", 0], ["2", 1], ["3", 2]]);' in page
    assert "<small>(2)</small>" in page and "<small>(3)</small>" in page
    assert "<b>2</b> thumbs-up" in page and "<b>1</b> average" in page


def test_any_of_the_three_keys_closes_the_fullscreen(tmp_path, store, stub_renders) -> None:
    """Matt's ruling of 2026-09-05, reversing the first reading. That reading was
    that clearing undoes a decision rather than taking one and should leave the
    picture up; in the hand Average IS a decision — "this one is ordinary" — and a
    key that sometimes closed and sometimes did not became the thing to keep track
    of, which is the objection that produced the three keys to begin with."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    pressing = page.split("function press(")[1].split("\n}")[0]
    assert "if (open === index) shut();" in pressing
    assert "&& kind" not in pressing, "Average is still an exception"


# --------------------------------------------------------------------------- #
# The viewer, 2.0.
# --------------------------------------------------------------------------- #
def test_the_fullscreen_bar_offers_all_three_states_in_key_order(
    tmp_path, store, stub_renders
) -> None:
    """Matt's ruling of 2026-09-05: Average, thumbs-up, star, left to right, in
    the order their keys are in. Average is a **state** and not the absence of
    one — it is what `1` does, and before 2.0 the only way to reach it with a
    mouse was to press an already-pressed button, which is why the fullscreen
    buttons now set rather than toggle."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    bar = page.split('<div id="big"')[1].split("</div>")[0]
    assert [found.group(1) for found in re.finditer(r'<button data-v="(\d)"', bar)] == [
        "0",
        "1",
        "2",
    ]
    assert "Average <small>(1)</small>" in bar
    assert "Thumbs up <small>(2)</small>" in bar
    assert "Star <small>(3)</small>" in bar


def test_the_thumbs_up_is_gold_and_the_star_is_green_everywhere_a_vote_shows(
    tmp_path, store, stub_renders
) -> None:
    """Two colours named once and read by the tile border, the button that cast
    the vote and the count strip. A person learns the pair on the first page, so
    a screen that spelled one of them differently would be teaching a second
    vocabulary for the same two votes."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert "--up: #fbbf24; --star: #16a34a;" in page
    for rule in (
        ".tally .up { color: var(--up); }",
        ".tally .star { color: var(--star); }",
        ".tile.up { border-color: var(--up); }",
        ".tile.star { border-color: var(--star); }",
    ):
        assert rule in page, rule
    assert '.bar button.on[data-v="1"] { background: var(--up);' in page
    assert '.bar button.on[data-v="2"] { background: var(--star);' in page
    # The old pair, gone rather than shadowed: a stale literal in the sheet is a
    # colour that comes back the next time somebody edits the rule above it.
    assert "#4ade80" not in page


def test_each_page_button_carries_the_votes_given_on_that_page(
    tmp_path, store, stub_renders
) -> None:
    """Over the viewer's own walk and not over the record — two people's page 3
    hold different pictures. Zero is drawn rather than left blank: a page nobody
    opened and a page somebody worked and liked nothing on are the same blank
    from the outside, and only the first is worth going back to."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert "function pageCounts()" in page and "function paintPager()" in page
    # Counted off `order`, which is the permutation, rather than off KEYS.
    assert "of order.slice(p * PER_PAGE, (p + 1) * PER_PAGE)" in page
    # Repainted by the one function every vote goes through, buttons and keys
    # alike, so a page turned under a fullscreen cannot leave a count behind.
    setting = page.split("function setVote(")[1].split("\n}")[0]
    assert "paintPager();" in setting
    assert "count.textContent = String(given);" in page


def test_starting_over_asks_twice_and_in_two_different_ways(tmp_path, store, stub_renders) -> None:
    """An in-page band carrying the count of what would go, then the browser's own
    dialog. Two steps of the same kind is one habit, and this is the only button
    in the viewer that destroys work."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert '<button id="reset">Start over</button>' in page
    assert 'id="confirm" hidden' in page
    # Step one shows the band and touches nothing: the count is read, not the
    # store written. A first step that already deleted would make the second a
    # formality.
    asking = page.split("function askReset()")[1].split("\n}")[0]
    assert 'document.getElementById("confirm").hidden = false;' in asking
    assert "removeItem" not in asking
    # Step two is the browser's own, and it is a guard clause: a refusal returns
    # before anything is dropped.
    erasing = page.split("function doReset()")[1].split("\n}")[0]
    assert "if (!window.confirm(" in erasing and "return;" in erasing
    assert erasing.index("window.confirm(") < erasing.index("removeItem")


def test_starting_over_clears_this_records_names_and_no_others(
    tmp_path, store, stub_renders
) -> None:
    """Every name that has used this browser goes, because the button is for
    leaving the computer clean — but another kit's folder is somebody else's
    evening, so the sweep is the record's own prefix.

    Handing the computer to a partner does not need it at all: a name is a slot,
    so they type theirs and the first person gets theirs back by typing hers."""
    built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert 'if (key && key.startsWith("votes/" + RECORD)) drop.push(key);' in page
    assert 'const SLOTS = "votes/" + RECORD + "/";' in page
    # The remembered name sits BESIDE the slot prefix rather than inside it: a
    # person actually called "name" would have overwritten it with their votes.
    assert 'const NAME_KEY = "votes/" + RECORD + ":name";' in page
    assert "function slot() { return SLOTS + who; }" in page


def test_the_paragraph_says_a_second_person_does_not_need_to_erase_anything(
    tmp_path, store, stub_renders
) -> None:
    """The README is the only thing a friend reads before opening anything, so
    the cheap way to share a computer has to be in it — otherwise the destructive
    button is the one they find."""
    built(tmp_path, store)
    text = (tmp_path / "kit" / votes.READ_ME).read_text(encoding="utf-8")
    assert "pick their own\nname" in text
    assert "erases every rating on the" in text and "asks you twice" in text


def test_the_export_says_which_viewer_a_friend_was_looking_at(
    tmp_path, store, stub_renders
) -> None:
    """3.0, and deliberately not `votes/v3`: telling it from the first version's
    `votes/v1` is telling two unrelated strings apart.

    1 and 2.0 were the same seven fields and the version named the page a person
    was looking at. **3.0 is the first that names the file**: four more fields,
    every one of them beside the seven rather than over them."""
    assert votes.VIEWER == "3.0"
    manifest = built(tmp_path, store)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert manifest["viewer"] == "3.0"
    assert 'const VIEWER = "3.0";' in page


def test_the_paragraph_the_friends_read_names_the_keys(tmp_path, store, stub_renders) -> None:
    """The README travels with the zip and is the only thing a friend reads before
    opening anything, so a key binding it does not carry is one nobody finds."""
    built(tmp_path, store)
    text = (tmp_path / "kit" / votes.READ_ME).read_text(encoding="utf-8")
    assert "2 for the thumbs-up, 3 for the star" in text
    assert "1 for an average one" in text
    assert "Any of the three closes the large picture" in text


# --------------------------------------------------------------------------- #
# One master permutation, rotated per friend.
# --------------------------------------------------------------------------- #
#: The names the deck tests build for. Three, so `round(i*N/F)` is not a halving,
#: and two of them carry a space and a dot so the slug rule is exercised by the
#: ordinary case rather than by a test written for it alone.
FRIENDS = ("Ada", "Bo Jones", "C.J.")


def built_for(tmp_path, stamp, friends, **over) -> dict:
    """A two-seat kit built for `friends`, at a fixed seed unless told another."""
    return votes.build(
        stamp=stamp,
        out=tmp_path / "kit",
        limit=2,
        friends=friends,
        seed=over.pop("seed", 12345),
        log=lambda _line: None,
        **over,
    )


def inlined(directory: Path, name: str):
    """`const <name> = ...;` as the page carries it, read back as JSON."""
    page = (directory / votes.PAGE_NAME).read_text(encoding="utf-8")
    found = re.search(rf"^const {name} = (.*);$", page, re.MULTILINE)
    assert found, f"the page does not inline {name}"
    return json.loads(found.group(1))


def test_the_master_permutation_is_a_permutation_and_its_seed_reproduces_it() -> None:
    """The seed is what regenerates a deck when the kit is gone, so it has to be
    the whole input. Two seeds that agreed would mean the seed said nothing."""
    assert sorted(votes.master_order(500, 7)) == list(range(500))
    assert votes.master_order(500, 7) == votes.master_order(500, 7)
    assert votes.master_order(500, 7) != votes.master_order(500, 8)
    assert votes.master_order(0, 7) == []


def test_a_friend_starts_an_even_share_of_the_way_into_the_same_order() -> None:
    """`round(i*N/F)`, and that is the whole coordination there is: no friend is
    told anything about another and the offsets do the spacing."""
    assert votes.deck_offsets(1000, ("a", "b", "c", "d")) == [0, 250, 500, 750]
    assert votes.deck_offsets(1000, ("a",)) == [0]
    assert votes.deck_offsets(7, ("a", "b", "c")) == [0, 2, 5]
    assert votes.deck_offsets(1000, ()) == []


def test_friends_who_each_finish_the_same_few_pages_have_voted_on_disjoint_pictures() -> None:
    """The property the rotation buys, and the reason it is a rotation rather than
    a per-person shuffle: eight friends who each work five pages of 25 have
    covered the thousand **exactly once between them**, with no overlap to throw
    away and no picture left unseen. Seven independent shuffles would be colliding
    at random from the first page."""
    order = votes.master_order(1000, 4242)
    friends = tuple(f"friend{index}" for index in range(8))
    reach = 5 * votes.PAGE
    seen = [
        seat
        for offset in votes.deck_offsets(1000, friends)
        for seat in votes.rotated(order, offset)[:reach]
    ]
    assert len(seen) == 1000
    assert sorted(seen) == list(range(1000))


def test_every_picture_collects_the_same_votes_for_the_same_total_effort() -> None:
    """Past the point where the decks lap each other the counts stay flat to
    within one, which is what "close to the same number of votes" means and the
    thing a prefix of a fixed order gets catastrophically wrong."""
    order = votes.master_order(1000, 99)
    friends = tuple(f"friend{index}" for index in range(7))
    reach = 12 * votes.PAGE
    counts = dict.fromkeys(range(1000), 0)
    for offset in votes.deck_offsets(1000, friends):
        for seat in votes.rotated(order, offset)[:reach]:
            counts[seat] += 1
    assert max(counts.values()) - min(counts.values()) <= 1


def test_the_order_file_is_the_deck_the_page_derives(tmp_path, store, stub_renders) -> None:
    """The files ship and the page never reads them — `file://` refuses to fetch a
    sibling — so the two are the same arithmetic written twice, and this is what
    holds them to agreeing."""
    manifest = built_for(tmp_path, store, FRIENDS)
    kit = tmp_path / "kit"
    order = inlined(kit, "ORDER")
    picks = inlined(kit, "DECKS")
    assert order == votes.master_order(2, manifest["deck"]["seed"])
    assert picks == [
        {"name": "Ada", "offset": 0},
        {"name": "Bo Jones", "offset": 1},
        {"name": "C.J.", "offset": 1},
    ]
    for row in manifest["deck"]["friends"]:
        held = json.loads((kit / row["file"]).read_text(encoding="utf-8"))
        assert held["name"] == row["name"]
        assert held["order"] == votes.rotated(order, row["offset"])
        assert held["order_seed"] == manifest["deck"]["seed"]
        assert held["page_size"] == votes.PAGE


def test_the_kit_carries_the_seed_and_the_offsets_it_was_built_with(
    tmp_path, store, stub_renders
) -> None:
    """A kit that did not would be a folder whose decks could never be rebuilt
    from what the friends were actually sent."""
    manifest = built_for(tmp_path, store, FRIENDS, seed=777)
    assert manifest["deck"]["seed"] == 777
    assert manifest["deck"]["page_size"] == votes.PAGE
    assert [row["file"] for row in manifest["deck"]["friends"]] == [
        "orders/Ada.json",
        "orders/Bo_Jones.json",
        "orders/C_J.json",
    ]
    held = json.loads((tmp_path / "kit" / votes.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert held["deck"] == manifest["deck"]
    assert held["record"] == store
    # The leg's own numbers stay out of the folder that goes to somebody else's
    # computer: this is what the kit IS, not what it cost to make.
    assert "render" not in held and "where" not in held


def test_a_rebuild_keeps_the_seed_the_friends_are_half_way_through(
    tmp_path, store, stub_renders
) -> None:
    """`--out` at a kit that exists is a resume. A re-drawn seed would rotate
    every page nobody had reached yet out from under them while leaving the votes
    they had already given attached to seats somewhere else entirely."""
    first = built_for(tmp_path, store, FRIENDS, seed=555)
    again = votes.build(
        stamp=store, out=tmp_path / "kit", limit=2, friends=FRIENDS, log=lambda _line: None
    )
    assert again["deck"]["seed"] == first["deck"]["seed"] == 555
    told = votes.build(
        stamp=store,
        out=tmp_path / "kit",
        limit=2,
        friends=FRIENDS,
        seed=556,
        log=lambda _line: None,
    )
    assert told["deck"]["seed"] == 556


@pytest.mark.parametrize("friends", [("Ada", "Ada"), ("Bo Jones", "Bo-Jones"), ("Ada", "  ")])
def test_two_friends_the_kit_cannot_tell_apart_are_refused_at_the_flag(
    tmp_path, store, friends
) -> None:
    """A collision is one friend handed two decks or two friends sharing a slot,
    and the slug is the order file's name. Found at the flag or not at all."""
    with pytest.raises(votes.VotesRefused):
        votes.build(stamp=store, out=tmp_path / "kit", friends=friends, log=lambda _line: None)


def test_the_first_screen_asks_who_they_are_and_the_pick_selects_the_deck(
    tmp_path, store, stub_renders
) -> None:
    """One zip for everybody — the pictures are not duplicated per person — so the
    page is what routes a friend to their own walk. A typed name survives only for
    the kit nobody was named in, where the same master order is rotated by a hash
    of it: one ordering rule, a worse offset."""
    built_for(tmp_path, store, FRIENDS)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert "function offsetFor(name)" in page
    assert 'button.addEventListener("click", () => begin(deck.name));' in page
    assert "return DECKS.length ? 0 : seedOf(name) % Math.max(1, ORDER.length);" in page
    # The deck is derived from the master order and an offset, never fetched:
    # `file://` refuses a sibling and the failure would be silent.
    assert "fetch(" not in page


def test_a_page_is_finished_by_the_button_that_says_so_and_by_nothing_else(
    tmp_path, store, stub_renders
) -> None:
    """*Go as far as you feel like, but finish any page you start* is the whole
    instruction, so a page somebody jumped to from the pager and left has to stay
    distinguishable from one they worked — which is what the flag on every row is
    for."""
    built_for(tmp_path, store, FRIENDS)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    finishing = page.split("function finishPage()")[1].split("\n}")[0]
    assert "completed.push(page)" in finishing
    drawing = page.split("function drawPage(next)")[1].split("\n}")[0]
    assert "completed" not in drawing, "turning a page marks it finished"
    assert 'document.getElementById("done").addEventListener("click", finishPage);' in page


def test_every_exported_row_carries_its_page_position_time_and_whether_it_was_finished(
    tmp_path, store, stub_renders
) -> None:
    """Additive: `votes` is still `{key: 1 | 2}` and the seven fields under it mean
    what they meant, so a reader that only knows 2.0 loses the new columns and
    nothing else. The trailing page of a partial pass stays in the file with
    `page_complete: false` — it is the one page whose votes were taken under a
    stopping decision, and dropping it would hide exactly that."""
    built_for(tmp_path, store, FRIENDS)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    building = page.split("function rows()")[1].split("\n}\n")[0]
    for field in ("key:", "vote:", "page:", "position:", "at:", "page_complete:"):
        assert field in building, field
    assert "position: seat % PER_PAGE," in building
    assert "page_complete: done.has(which)," in building
    shape = page.split("function exported()")[1].split("\n}\n")[0]
    for field in ("viewer:", "record:", "name:", "order_seed:", "votes:", "pages_visited:"):
        assert field in shape, field
    for field in ("deck_offset:", "page_size:", "pages_completed:", "rows: rows()"):
        assert field in shape, field
    # The labeler is the name that was submitted and never one this tool infers.
    assert "name: who," in shape


def test_the_page_probes_storage_and_says_so_when_the_browser_refuses_it(
    tmp_path, store, stub_renders
) -> None:
    """Chromium, Firefox and WebKit were all measured keeping `localStorage`
    across a browser restart from a `file://` URL. **Safari itself could not be**
    — it is macOS and iOS only — and it has refused local storage on `file://`
    before, so the page probes rather than trusts: a page that only wrapped its
    writes would keep nothing there and still say the choices were being saved.
    The band is on screen and the way back is the friend's own export, which is
    also the way back for a friend who changed computers — so it is offered in
    every browser rather than only a broken one."""
    built_for(tmp_path, store, FRIENDS)
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert 'localStorage.setItem("votes/probe", "1");' in page
    assert "function paintStorage()" in page
    assert 'id="nostore"' in page
    assert "function resumeFrom(text)" in page
    assert "if (held.record !== RECORD)" in page
    assert 'accept=".json,application/json"' in page


def test_a_page_is_twenty_five_pictures(tmp_path, store, stub_renders) -> None:
    """Down from 100 on 2026-09-09, and it is a unit of *finishing* rather than of
    layout: a page has to be short enough that starting one is not a commitment
    somebody regrets, because finishing the one you start is what Matt asks."""
    assert votes.PAGE == 25
    manifest = built_for(tmp_path, store, FRIENDS, per_page=10)
    assert manifest["deck"]["page_size"] == 10
    page = (tmp_path / "kit" / votes.PAGE_NAME).read_text(encoding="utf-8")
    assert "const PER_PAGE = 10;" in page
