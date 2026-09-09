"""What became of every wallpaper somebody graded 4.

Three things here and they fail differently.

**The rung ladder** is the claim: a picture stops at the first rung that holds
it, and the five are exclusive and ordered. What is pinned is that each rung is
decided by the condition it *names* — the roster before any bar, the coarse bar
before the fine one — because the whole reason rung 0 exists is that calling an
off-roster row *below the coarse bar* would say a bar refused a picture no bar
ever read. A ladder that tested the bars first would still produce five buckets
and every count in the report would be wrong.

**The refusals to proceed** are the second half, and they are the guard against
a page that reads plausibly and answers about the wrong record. `fates` refuses a
solve with no `explained` block and one whose block does not name this
population, because a rung inferred from the aggregate refusal columns would be a
guess about which of several rules acted first — and a guess is exactly what
joining the labels to the ledger by key was supposed to end.

**Everything else is arithmetic** — the store's paths, which side of a card a key
is wanted for, the sort the page is in — and can only be wrong about counting.

Every test here is fast: nothing renders, nothing reads this machine's ledger,
and each one hands in its own rows.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import label_fate, release, solve
from fractal_wallpapers.labeling.sheets import LABEL_RESOLUTION, LABEL_SUPERSAMPLE


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def population_row(**over) -> dict:
    """One row of `population.jsonl`, cleared by both bars and undecided above them."""
    row = {
        "schema": 1,
        "key": "aaaa000000000001",
        "verdicts": [{"store": "smooth_render", "grade": 4, "batch": "b", "labeler": None}],
        "stores": ["smooth_render"],
        "in_the_ledger": True,
        "mode": "smooth",
        "routed_mode": "smooth",
        "mode_params": {},
        "colormap": "glassworks-25",
        "palette_group": "map:glassworks-25",
        "location": '["multibrot3", 3, [], "-0.5", "0.6", "1e-05"]',
        "partition": "multibrot3",
        "picture": "a.jpg",
        "p_ge4": 0.9,
        "p_ge3": 0.99,
        "p_fine": 0.8,
        "p_fine_from": "pool",
        "rung": None,
        "why": None,
    }
    row.update(over)
    return row


def write_population(store, rows) -> None:
    path = label_fate.store_root(store) / label_fate.POPULATION_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


# --------------------------------------------------------------------------- #
# The ladder.
# --------------------------------------------------------------------------- #
def test_the_five_rungs_are_named_once_and_in_the_order_a_picture_meets_them():
    assert [name for name, _ in label_fate.RUNGS] == [
        label_fate.OFF_THE_ROSTER,
        label_fate.BELOW_COARSE,
        label_fate.BELOW_FINE,
        label_fate.REFUSED,
        label_fate.SEATED,
    ]
    assert len({name for name, _ in label_fate.RUNGS}) == 5


def test_an_off_roster_row_is_rung_zero_and_not_below_a_bar_it_never_met():
    """The ladder's whole reason for having a rung 0.

    A row in a mode the roster weights 0 also has no score, so a ladder that
    asked the coarse bar first would call it `below_the_coarse_bar` — which says
    a bar refused a picture that no bar was ever applied to, and would put every
    niche-mode verdict into the count the report reads as *the head disagreed*.
    """

    class Roster:
        @staticmethod
        def is_accepted(mode):
            return mode == "smooth"

    off = label_fate._off_the_roster(
        {"key": "k", "rejected": False, "at_candidate_regime": True, "picture": "a.jpg"},
        "gaussian_int",
        {"k"},
        {"p_ge4": 0.99},
        Roster,
    )
    assert off == "mode gaussian_int is off the roster"


@pytest.mark.parametrize(
    "row,routed,present,read,expected",
    [
        (None, None, set(), {}, "no ledger row"),
        (
            {"key": "k", "rejected": True, "at_candidate_regime": True, "picture": "a.jpg"},
            "smooth",
            {"k"},
            {"p_ge4": 0.9},
            "somebody rejected it",
        ),
        (
            {"key": "k", "rejected": False, "at_candidate_regime": False, "picture": "a.jpg"},
            "smooth",
            {"k"},
            {"p_ge4": 0.9},
            "not at candidate regime",
        ),
        (
            {"key": "k", "rejected": False, "at_candidate_regime": True, "picture": None},
            "smooth",
            {"k"},
            {"p_ge4": 0.9},
            "the row names no picture",
        ),
        (
            {"key": "k", "rejected": False, "at_candidate_regime": True, "picture": "a.jpg"},
            "smooth",
            set(),
            {"p_ge4": 0.9},
            "its picture is not on disk",
        ),
        (
            {"key": "k", "rejected": False, "at_candidate_regime": True, "picture": "a.jpg"},
            "smooth",
            {"k"},
            {},
            "no reading on the live judge",
        ),
        (
            {"key": "k", "rejected": False, "at_candidate_regime": True, "picture": "a.jpg"},
            "smooth",
            {"k"},
            {"p_ge4": 0.9},
            None,
        ),
    ],
)
def test_rung_zero_is_solve_pools_own_exclusions_and_all_of_them(
    row, routed, present, read, expected
):
    """Each of the five reasons `solve.pool` refuses a row, plus the missing row.

    Stated one by one rather than as a count, because a row that is off the pool
    for a reason this leg does not know about would otherwise be silently graded
    against a bar — and the failure would look like a surprising rung-1 count
    rather than like a bug.
    """

    class Roster:
        @staticmethod
        def is_accepted(mode):
            return mode == "smooth"

    assert label_fate._off_the_roster(row, routed, present, read, Roster) == expected


def test_this_module_defines_no_bar_of_its_own():
    """A bar spelled twice is a bar that drifts from the one the solve runs.

    Both heights come off `solve` at the moment they are read, so a ruling that
    moves either moves this leg's rungs with it. The failure a second spelling
    would cause is the worst kind available here: every count in the report stays
    plausible and describes a bar production stopped using.
    """
    held = {
        name
        for name in vars(label_fate)
        if name.isupper() and (name == "BAR" or name.endswith("_BAR") or name.startswith("BAR_"))
    }
    assert held == set(), f"{label_fate.__name__} spells a bar of its own: {sorted(held)}"
    assert solve.Q4_BAR == 0.50
    assert solve.DEFAULT_FINE_BAR == 0.50


def test_counting_a_rung_leaves_the_undecided_out():
    rows = [
        population_row(rung=label_fate.SEATED),
        population_row(rung=label_fate.SEATED),
        population_row(rung=label_fate.BELOW_FINE),
        population_row(rung=None),
    ]
    assert label_fate._counted(rows) == {
        label_fate.OFF_THE_ROSTER: 0,
        label_fate.BELOW_COARSE: 0,
        label_fate.BELOW_FINE: 1,
        label_fate.REFUSED: 0,
        label_fate.SEATED: 2,
    }


# --------------------------------------------------------------------------- #
# The refusals.
# --------------------------------------------------------------------------- #
def test_fates_refuses_a_record_that_carries_no_explained_block(tmp_path, monkeypatch):
    store = tmp_path / "fate"
    write_population(store, [population_row()])
    monkeypatch.setattr(
        "fractal_wallpapers.curation.tentative.read_manifest",
        lambda stamp: {
            "solve": {
                "name": "a_record",
                "record": "artifacts/curation/solve/a_record/solve.json",
            }
        },
    )
    monkeypatch.setattr(
        "fractal_wallpapers.curation.solve.read_record", lambda name: {"rejection": {}}
    )
    with pytest.raises(label_fate.FateRefused, match="no `rejection.explained` block"):
        label_fate.fates("20260101T000000Z", store, log=quiet)


def test_fates_refuses_a_block_that_was_asked_about_another_population(tmp_path, monkeypatch):
    """The failure this is really for is silent.

    A record explained over an earlier population answers for the keys it shares
    and says nothing about the rest, so a leg that filled what it could would
    produce a page whose rung counts are about two different questions at once.
    """
    store = tmp_path / "fate"
    write_population(store, [population_row(key="aaaa1"), population_row(key="bbbb2")])
    monkeypatch.setattr(
        "fractal_wallpapers.curation.tentative.read_manifest",
        lambda stamp: {
            "solve": {
                "name": "a_record",
                "record": "artifacts/curation/solve/a_record/solve.json",
            }
        },
    )
    monkeypatch.setattr(
        "fractal_wallpapers.curation.solve.read_record",
        lambda name: {"rejection": {"explained": {"aaaa1": "seated"}}},
    )
    with pytest.raises(label_fate.FateRefused, match="not in .*`explained` block"):
        label_fate.fates("20260101T000000Z", store, log=quiet)


def test_a_stage_refuses_a_store_the_stage_before_it_never_wrote(tmp_path):
    store = tmp_path / "empty"
    with pytest.raises(label_fate.FateRefused, match="Run `population` first"):
        label_fate.fates("20260101T000000Z", store, log=quiet)


def test_fates_refuses_a_manifest_that_names_no_solve_record(tmp_path, monkeypatch):
    """A stamp whose record is gone is a gallery nothing can be asked about.

    Worth its own refusal rather than a `KeyError`: the seats are still there and
    still readable, so the failure is specifically *why did this row lose*, and a
    traceback out of a dict lookup does not say that.
    """
    store = tmp_path / "fate"
    write_population(store, [population_row()])
    monkeypatch.setattr(
        "fractal_wallpapers.curation.tentative.read_manifest", lambda stamp: {"seats": {}}
    )
    with pytest.raises(label_fate.FateRefused, match="names no solve record"):
        label_fate.fates("20260101T000000Z", store, log=quiet)


# --------------------------------------------------------------------------- #
# The geometry, and the two sides of a card.
# --------------------------------------------------------------------------- #
def test_the_page_geometry_is_the_label_geometry_and_the_release_geometry_at_once():
    """The claim that makes the side-by-side fair, pinned on both constants.

    A graded picture and a shipped wallpaper are the same size today, which is
    why this leg can draw both sides once and compare them. If either constant
    moves, the pair stops being a comparison at one size and `render` refuses
    rather than quietly drawing two.
    """
    assert tuple(release.RELEASE_REGIME.resolution) == tuple(LABEL_RESOLUTION)
    assert release.RELEASE_REGIME.supersample == int(LABEL_SUPERSAMPLE)


def test_a_release_task_carries_every_keyed_member_the_picture_depends_on():
    """`mode_params`, `curve` and `palette` are all recipe-key members.

    A task missing one renders a picture of something else under the row's own
    name, which is what `mine.make` did with `mode_params` for six days without
    anything going red.
    """
    task = release.Task(
        id="k",
        row={},
        colormap="a-map",
        mode="smooth",
        output="out.jpg",
        geometry={},
        mode_params={"opacity": 0.6},
        curve="log",
        palette={"gamma": 0.75},
    )
    assert task.mode_params == {"opacity": 0.6}
    assert task.curve == "log"
    assert task.palette == {"gamma": 0.75}


def test_a_task_that_names_neither_override_is_the_candidate_path_unchanged():
    task = release.Task(id="k", row={}, colormap="a-map", mode="smooth", output="o", geometry={})
    assert task.curve is None
    assert task.palette is None
    assert task.mode_params == {}


def test_a_wallpaper_that_took_the_seat_at_its_own_place_is_drawn_once():
    """Both sides of that card are one picture, so keying the render on the card
    would draw it twice and the page would compare a file with its own copy."""
    key = "aaaa000000000001"
    wanted = label_fate._wanted([population_row(key=key, seat={"key": key})])
    assert list(wanted) == [key]
    assert wanted[key] == ["graded", "seat"]


def test_a_place_with_no_seat_wants_only_the_graded_side():
    wanted = label_fate._wanted([population_row(seat=None)])
    assert wanted == {"aaaa000000000001": ["graded"]}


def test_a_row_the_ledger_does_not_hold_is_wanted_on_neither_side():
    """It has no recipe, so there is nothing to draw and the card says so."""
    assert label_fate._wanted([population_row(in_the_ledger=False, seat=None)]) == {}


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def test_a_staged_reading_is_marked_and_a_pool_reading_is_not():
    """The mark is the whole point: a rung-1 row's `p_fine` is a number production
    never computed, and showing it unmarked would say the head read a row it is
    defined not to have read."""
    assert label_fate._score(0.25, marked=True) == '<span class="staged">0.2500*</span>'
    assert label_fate._score(0.25) == "0.2500"
    assert "—" in label_fate._score(None)


def test_a_varied_key_is_spelled_with_its_settings_and_a_bare_one_is_not():
    assert label_fate._mode("direct_trap_multiply", {}) == "direct_trap_multiply"
    assert (
        label_fate._mode("direct_trap_multiply", {"opacity": 0.6, "threshold": 0.2})
        == "direct_trap_multiply@opacity=0.6,threshold=0.2"
    )


def test_a_varied_row_is_flagged_on_its_MAKER_and_not_on_its_settings():
    """The flag is a claim about which renderer drew the stored picture.

    `hunt` and `label_migration` have always passed the settings, so a varied row
    under either is what its key says; a `depth` row went through `mine.make` and
    is the bare mode. Flagging on the settings alone would mark 15 correct
    `label_migration` pictures on this page, and never flagging would hide 43.
    """
    depth = population_row(
        mode_params={"opacity": 0.6},
        picture="artifacts/curation/depth/dtm_known_full/pictures/k.jpg",
    )
    migrated = population_row(
        mode_params={"opacity": 0.6},
        picture="artifacts/curation/label_migration/label_migration_0908/pictures/k.jpg",
    )
    hunted = population_row(
        mode_params={"opacity": 0.6},
        picture="artifacts/curation/hunt/a_hunt/pictures/k.jpg",
    )
    bare = population_row(picture="artifacts/curation/depth/dtm_known_full/pictures/k.jpg")
    assert label_fate.drawn_bare(depth, set()) is True
    assert label_fate.drawn_bare(migrated, set()) is False
    assert label_fate.drawn_bare(hunted, set()) is False
    assert label_fate.drawn_bare(bare, set()) is False
    assert label_fate.drawn_bare(depth, {depth["key"]}) is False


def test_a_windows_picture_path_names_its_leg_the_same_as_a_posix_one():
    """Every path in this store was written on Windows and is read on both."""
    windows = "C:" + chr(92) + "Code" + chr(92)
    windows += chr(92).join(["artifacts", "curation", "depth", "dtm_known_full", "p", "k.jpg"])
    assert label_fate.leg_of(windows) == "depth/dtm_known_full"
    assert label_fate.leg_of("artifacts/curation/hunt/a_hunt/pictures/k.jpg") == "hunt/a_hunt"
    assert label_fate.leg_of(None) == ""
    assert label_fate.leg_of("nowhere/k.jpg") == ""


def test_an_unflagged_varied_row_still_says_it_carries_settings():
    varied = population_row(
        mode_params={"opacity": 0.6},
        rung=label_fate.SEATED,
        picture="artifacts/curation/depth/d/pictures/k.jpg",
    )
    flagged = label_fate._card(varied, None, None, set())
    assert "drawn bare under a varied key" in flagged
    settled = label_fate._card(varied, None, None, {varied["key"]})
    assert "drawn bare under a varied key" not in settled
    assert "varied key" in settled


def test_a_card_with_no_seat_says_so_rather_than_leaving_a_gap():
    """On a rung that pairs by PLACE. A refused card is a different silence and
    says a different thing — see the same-place guard above."""
    card = label_fate._card(
        population_row(seat=None, rung=label_fate.BELOW_FINE), None, None, set()
    )
    assert "no seat at this place" in card
    assert "the record holds nothing here" in card


def test_a_refused_card_names_the_first_rule_and_the_page_says_it_is_the_first():
    row = population_row(rung=label_fate.REFUSED, why="cell_allowance", seat=None)
    assert "first refused by" in label_fate._card(row, None, None, set())
    assert "FIRST" in dict(label_fate.RUNGS)[label_fate.REFUSED].upper()


def test_the_legend_counts_every_rung_even_the_empty_ones():
    rows = [population_row(rung=label_fate.SEATED)]
    legend = label_fate._legend(rows, label_fate._counted(rows), {}, set())
    for name, _ in label_fate.RUNGS:
        assert label_fate._title(name) in legend


def test_the_legend_says_both_columns_are_contaminated_and_which_is_which():
    """The prompt asked for one caveat; the population needed two.

    Every gallery-grade row is inside the fine head's own corpus, so `p_fine` is
    the honest column for the two finished-render stores and recognition for the
    third — and a legend carrying only the coarse caveat would recommend the
    contaminated column to a reader.
    """
    rows = [
        population_row(stores=["gallery_grade"], rung=label_fate.SEATED),
        population_row(stores=["smooth_render"], rung=label_fate.SEATED),
    ]
    legend = label_fate._legend(rows, label_fate._counted(rows), {}, set())
    assert "Both score columns are contaminated" in legend
    assert "no one honest column over this page" in legend
    assert "1.1%" in legend
    assert f"{label_fate.JUDGE_TRAIN:,}" in legend


# --------------------------------------------------------------------------- #
# The pairing, and the two questions it is not allowed to conflate.
# --------------------------------------------------------------------------- #
def test_every_refusing_rule_says_what_it_pairs_with():
    """A rule with no entry would pair silently with nothing and read as a bug in
    the record rather than as a gap in this table."""
    assert set(label_fate.PAIRING) == {
        "location",
        "cell_allowance",
        "twin",
        "another_place_is_the_same_place",
    }


def test_the_refusing_set_is_the_rule_that_ACTED_and_not_the_intersection():
    """The bug this replaced, kept as a guard.

    `removals` is the intersection across *every* rule a candidate fails, and
    answers "would one seat leaving be enough". A row the location rule took that
    also fails the cell allowance has an empty intersection — 101 of this page's
    102 location refusals do — so pairing on `removals` showed those cards
    nothing, while the seat standing at their place plainly beat them.
    """

    class Rule:
        @staticmethod
        def allowed(name, n):
            return 1

    class State:
        places = {"here": "the_seat"}
        cells = {"blue": {"seat_a": True, "seat_b": True}}
        rule = Rule()
        n = 10

        @staticmethod
        def counted_removals(_candidate):
            return set()

    class Candidate:
        location = "here"
        cells = ("blue",)

    assert label_fate._refusing_set(State, Candidate, "location") == {"the_seat"}
    assert label_fate._refusing_set(State, Candidate, "cell_allowance") == {"seat_a", "seat_b"}
    assert State.counted_removals(Candidate) == set()


def test_the_first_over_full_cell_is_the_one_that_refused():
    """`counted_refusal` returns on the first over-full cell in the candidate's own
    order, so the set has to come off that cell and not off whichever comes last."""

    class Rule:
        @staticmethod
        def allowed(name, n):
            return 99 if name == "roomy" else 1

    class State:
        places: dict = {}
        cells = {"roomy": {"a": True}, "full": {"b": True, "c": True}}
        rule = Rule()
        n = 10

    class Candidate:
        location = "nowhere"
        cells = ("roomy", "full")

    assert label_fate._refusing_set(State, Candidate, "cell_allowance") == {"b", "c"}


def test_a_same_place_refusal_is_paired_with_nothing_and_the_card_says_why():
    """It was refused at POOL CONSTRUCTION, before a seat existed, so there is no
    seat to name. A card that fell back to the place's seat would name a picture
    that never competed with it."""
    row = population_row(rung=label_fate.REFUSED, explained="another_place_is_the_same_place")
    assert label_fate._against(row) == (None, None)
    card = label_fate._card(row, None, None, set())
    assert "no row to name" in card
    assert "folded this place into a neighbour" in card


def test_a_refused_card_pairs_on_the_competitor_and_every_other_rung_on_the_place():
    """Two different pairings, and the rung decides which."""
    refused = population_row(
        rung=label_fate.REFUSED,
        explained="cell_allowance",
        competitor={"key": "rival01", "why": "cell_allowance"},
        seat={"key": "seat01"},
    )
    assert label_fate._against(refused)[0] == "rival01"
    seated = population_row(rung=label_fate.SEATED, seat={"key": "seat01", "seat": 3})
    assert label_fate._against(seated)[0] == "seat01"


def test_the_gap_is_on_the_card_because_0_01_and_0_4_are_different_findings():
    row = population_row(
        rung=label_fate.REFUSED,
        explained="cell_allowance",
        p_fine=0.5002,
        competitor={
            "key": "rival01",
            "why": "cell_allowance",
            "mode": "smooth",
            "colormap": "a-map",
            "p_fine": 0.9,
            "gap": 0.3998,
            "alternatives": 42,
        },
    )
    card = label_fate._card(row, None, "a.jpg", set())
    assert "+0.3998" in card
    assert "marginal of 42 seats" in card


def test_a_card_says_when_no_single_departure_would_have_been_enough():
    row = population_row(
        rung=label_fate.REFUSED,
        explained="location",
        competitor={"key": "r", "why": "location", "alternatives": 1, "enough": []},
    )
    assert "no single seat leaving would have been enough" in label_fate._card(
        row, None, "a.jpg", set()
    )


# --------------------------------------------------------------------------- #
# The split.
# --------------------------------------------------------------------------- #
def test_the_dropped_rung_is_counted_and_not_shown():
    """117 rows in weight-0 modes: no bar read them and no rule refused them, so a
    section of them would claim a comparison that does not exist. The index still
    carries the count, so the rungs add to the population."""
    assert label_fate.NOT_SHOWN == (label_fate.OFF_THE_ROSTER,)
    rows = [
        population_row(rung=label_fate.OFF_THE_ROSTER),
        population_row(rung=label_fate.SEATED, seat=None),
    ]
    stems = {one["stem"] for one in label_fate._slices(rows)}
    assert label_fate.slug(label_fate.OFF_THE_ROSTER) not in stems
    assert label_fate._counted(rows)[label_fate.OFF_THE_ROSTER] == 1


def test_the_cut_follows_the_sort_and_never_reorders_it():
    """Page 1 of a rung has to be the head of the sort, or the whole point of
    sorting ascending is lost to whoever opens page 1."""
    rows = [
        population_row(key=f"k{at:04d}", rung=label_fate.BELOW_FINE, p_fine=at / 1000, seat=None)
        for at in range(320)
    ]
    mine = [one for one in label_fate._slices(rows) if one["stem"] == "below-the-fine-bar"]
    assert [one["file"] for one in mine] == [
        "below-the-fine-bar-01.html",
        "below-the-fine-bar-02.html",
        "below-the-fine-bar-03.html",
    ]
    assert [len(one["rows"]) for one in mine] == [150, 150, 20]
    ordered = [row["p_fine"] for one in mine for row in one["rows"]]
    assert ordered == sorted(ordered)
    assert ordered[0] == 0.0


def test_the_refused_rung_is_written_twice_and_the_by_rule_pages_are_the_same_cards():
    rows = [
        population_row(key="a", rung=label_fate.REFUSED, explained="cell_allowance", seat=None),
        population_row(key="b", rung=label_fate.REFUSED, explained="location", seat=None),
    ]
    slices = label_fate._slices(rows)
    stems = {one["stem"] for one in slices}
    assert "refused" in stems
    assert "refused-cell-allowance" in stems
    assert "refused-location" in stems
    plain = sum(len(one["rows"]) for one in slices if one["stem"] == "refused")
    by_rule = sum(len(one["rows"]) for one in slices if one["by_rule"])
    assert plain == by_rule == 2


def test_a_page_name_is_guessable_and_a_rule_name_survives_the_slug():
    assert label_fate.slug("below_the_fine_bar") == "below-the-fine-bar"
    assert label_fate.slug("another_place_is_the_same_place") == "another-place-is-the-same-place"


def test_every_page_carries_prev_next_and_a_way_back_to_the_index():
    rows = [
        population_row(key=f"k{at:04d}", rung=label_fate.BELOW_FINE, p_fine=at / 1000, seat=None)
        for at in range(320)
    ]
    slices = [one for one in label_fate._slices(rows) if one["stem"] == "below-the-fine-bar"]
    first, middle, last = (label_fate._nav(one, slices) for one in slices)
    assert label_fate.PAGE_NAME in first and "prev" not in first and "next" in first
    assert "prev" in middle and "next" in middle
    assert "prev" in last and "next" not in last


def test_the_two_contamination_counts_are_memberships_and_not_a_partition():
    """29 wallpapers are graded 4 in a finished store AND in the gallery-grade
    sitting, and both figures beside the counts were measured over the whole
    membership. Splitting the overlap into one bucket would divide a numerator by
    the wrong denominator — quietly, and in the direction of understating it."""
    both = population_row(stores=["smooth_render", "gallery_grade"], rung=label_fate.SEATED)
    legend = label_fate._legend([both], label_fate._counted([both]), {}, set())
    assert "<b>1</b> rows a finished store grades 4" in legend
    assert "<b>1</b> gallery-grade rows" in legend


def test_the_fine_heads_two_sides_account_for_every_gallery_grade_row():
    """The claim the legend makes: that store IS the fine head's corpus.

    Stated as arithmetic so the day a sitting adds rows without a re-fit, this
    fails rather than the page going on saying `every one`.
    """
    from fractal_wallpapers.labeling import gallery_grade

    assert label_fate.FINE_TRAIN + label_fate.FINE_STOPPING == 312
    assert gallery_grade.NAME == "gallery_grade"
