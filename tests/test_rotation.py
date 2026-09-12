"""The rotation pass: what it will not touch, what it draws, and what it decides.

Arithmetic over records, like [`test_remode`] and for the same reason: away from
the half-second a recolour takes, this module is a filter over the ledger, a
seeded draw and a `max`. So there is a fake ledger and never a picture, and the
one guard that does drive the engine is where the store's own suite already keeps
that cost — `test_renderer_agreement.py`, which holds every path that turns a
recipe into a picture to drawing the same one. This pass renders through
[`mine.make`] precisely so that it is covered there without being registered here.

The properties worth pinning hardest are the ones that make the pass **safe**
rather than the ones that make it work, because what it does is delete rows:

* the draw moves `phase` and nothing else, and `cycles` stays the identity;
* a row a guard holds is adopted from and never removed from;
* the tolerance is a factor of the **stored** column, which is the only reading
  that can refuse anything at all;
* and [`sweep.remove`] writes its loss down, because a row that left the store
  with no transaction accounting for it is what the ratchet exists to catch.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import candidate_ledger, recipes, rotation
from fractal_wallpapers.curation.candidate_ledger import ratchet, sweep
from fractal_wallpapers.curation.candidate_ledger import store as store_module
from fractal_wallpapers.labeling import finished

VIEWPORT = {"center_re": "-0.5", "center_im": "0.1", "width": "0.004", "rotation": 0.0}


# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
def a_recipe(mode="smooth", colormap="magma", palette=None, curve="linear", mode_params=None):
    """One recipe, in the shape a stored row carries it."""
    return recipes.Recipe(
        family={"kind": "mandelbrot", "degree": 2},
        viewport=dict(VIEWPORT),
        maxiter=8080,
        regime=recipes.CANDIDATE_REGIME,
        mode=mode,
        mode_params=dict(mode_params or {}),
        curve=curve,
        colormap=colormap,
        palette=palette or finished.recipe(mirror=True),
        autolevel=recipes.live_stamp(mode),
        palette_group=f"map:{colormap}",
    )


def a_row(key="k0", place="p0", **over):
    """One ledger row, thinned to what this module reads off one."""
    recipe = over.pop("recipe", None) or a_recipe(**over.pop("recipe_of", {}))
    row = {
        "schema": 1,
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": place, "agrees": True},
        "recipe": recipe.record(),
        "at_candidate_regime": True,
        "picture": f"artifacts/curation/depth/leg/pictures/{key}.jpg",
        "provenance": {"run": "leg", "candidate": "00001", "also_recorded": []},
        "rejected": None,
    }
    row.update(over)
    return row


def an_incumbent(key="k0", place="p0", p_fine=0.5, held_by=None, **over):
    return rotation.Incumbent(
        key=key,
        location=place,
        partition="mandelbrot",
        mode=over.pop("mode", "smooth"),
        colormap=over.pop("colormap", "magma"),
        picture=f"artifacts/curation/depth/leg/pictures/{key}.jpg",
        p_fine=float(p_fine),
        recipe=(over.pop("recipe", None) or a_recipe()).record(),
        held_by=held_by,
    )


KINDS = {
    "smooth": "field",
    "stripe": "field",
    "threads": "composite",
    "itinerary": "modulate",
    "direct_trap_ring": "direct",
}


# --------------------------------------------------------------------------- #
# The subtree.
# --------------------------------------------------------------------------- #
def test_the_passs_pictures_are_reachable_by_the_orphan_sweep():
    """Not a spelling check, and it matters more here than at any other leg.

    `candidate_ledger.orphans` enumerates `POOL_SUBTREES` and no other names. This
    pass draws five rotations a row and adopts at most one, so **five-sixths of
    what it makes is garbage by design** — and a pass killed between rendering a
    chunk and deciding it leaves that whole chunk named by nothing, with no row
    anywhere and nothing able to find it.
    """
    assert rotation.UNIT in candidate_ledger.POOL_SUBTREES
    assert rotation.pictures_dir("pass").name == candidate_ledger.PICTURES_NAME
    assert rotation.pictures_dir("pass").parent.parent.name == rotation.UNIT


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
def test_the_draw_is_seeded_off_the_row_so_a_partial_pass_repeats_itself():
    """A row's phases are a function of `(seed, its key)` and of nothing else.

    Seeded off a stream shared by the pass, a row's phases would depend on how
    many rows came before it — so a pass that stopped at the clock and a pass
    re-run over the same population would ask *different questions* of the same
    rows, and the second one's answers could not be read beside the first one's.
    """
    first = rotation.draws("abc", seed=7)
    assert first == rotation.draws("abc", seed=7)
    assert first != rotation.draws("abd", seed=7)
    assert first != rotation.draws("abc", seed=8)
    assert len(first) == rotation.ROTATIONS
    assert all(0.0 <= phase < 1.0 for phase in first)
    assert len(set(first)) == len(first), "a row asking one phase twice pays twice for one answer"


def test_the_draw_moves_the_phase_and_leaves_the_repeat_at_the_identity():
    """`Palette.cycles` is not on the table and the intention must not carry one.

    `palette_variant_mine_ckpt120` measured the repeat axis as monotonically
    destructive — 36.4% of matched pairs won at repeat 3 against 52.6% at repeat 1
    — so this pass fixes it at [`rotation.REPEAT`]. The guard is on the
    **intention**, because that is what `hunt.Maker.palette_for` spends: a
    `cycles` here would be a member of the recipe key and a second axis in a pass
    that ruled on one.
    """
    incumbent = an_incumbent()
    groups, shape = rotation.plan_of([incumbent], seed=3, known=set())
    ((_source, made),) = groups[0]
    assert shape["rotations"] == rotation.ROTATIONS
    for rotation_of in made:
        assert set(rotation_of.palette) == {"phase"}
        assert rotation_of.palette["phase"] == rotation_of.phase
        assert rotation_of.mode_params == {}
    assert rotation.REPEAT == 1


def test_a_rotation_carries_the_knobs_its_incumbents_pass_carries():
    """The 43 rows `rotation_pass_ckpt120` refused, and why they were not misfiled.

    All 43 digest back to their own key out of their own stored recipe, as all
    374,309 rows in the store do. What did not reproduce was the REBUILD, which
    was built at `finished.recipe`'s defaults where their pass carries a tuned
    `gamma` — no candidate leg draws one, the label-import path wrote it, and all
    43 carry a human label. So the rotation carries the difference forward and the
    rebuilt phase 0 is the row again.
    """
    tuned = a_recipe(palette=finished.recipe(mirror=True, gamma=1.2778, reverse=True))
    incumbent = an_incumbent(recipe=tuned)
    assert incumbent.pass_knobs() == {"gamma": 1.2778, "reverse": True}
    groups, _shape = rotation.plan_of([incumbent], seed=3, known=set())
    ((_source, made),) = groups[0]
    for rotation_of in made:
        assert rotation_of.palette == {
            "gamma": 1.2778,
            "reverse": True,
            "phase": rotation_of.phase,
        }


def test_an_ordinary_rows_rotation_carries_its_phase_and_nothing_else():
    """The overrides are the DIFFERENCE from the plain pass and not the pass, so a
    row nobody tuned does not come out looking like a varied draw on its record."""
    assert an_incumbent().pass_knobs() == {}


def test_a_rotation_names_the_row_it_rotates_because_nothing_else_records_it():
    """A rotation differs from its incumbent in the palette and in nothing else,
    so the ledger's own shape has no field that says *made from*. The `hunt` block
    carries it, which is the only join this pass leaves behind."""
    made = rotation.Rotation(
        of_key="k0",
        location="p0",
        partition="mandelbrot",
        mode="smooth",
        colormap="magma",
        k=2,
        phase=0.25,
        palette={"phase": 0.25},
    )
    named = made.named()
    assert named["rotation_of"] == "k0"
    assert named["k"] == 2
    assert named["palette_drawn"] == {"phase": 0.25}
    assert candidate_ledger.hunt_block({"seconds": 1.0, **named})["k"] == 2


def test_the_plan_cuts_at_the_pair_and_keeps_store_order():
    """The group is the unit because one dumped field serves every rotation under
    it, and the order inside is the order the rows arrived in.

    The ordering is the whole de-biasing argument rather than a convenience: a
    plan that took the best rows first would re-select the population this pass
    exists to un-select.
    """
    rows = [
        an_incumbent(key="a", place="p0", p_fine=0.1),
        an_incumbent(key="b", place="p1", p_fine=0.9),
        an_incumbent(key="c", place="p0", p_fine=0.5),
        an_incumbent(key="d", place="p0", mode="stripe", p_fine=0.2),
    ]
    groups, shape = rotation.plan_of(rows, seed=0, known=set())
    assert [[source.key for source, _made in group] for group in groups] == [
        ["a", "c"],
        ["b"],
        ["d"],
    ]
    assert shape["groups"] == 3
    assert shape["rows"] == 4
    assert shape["rows_a_group"] == pytest.approx(4 / 3, abs=1e-3)


# --------------------------------------------------------------------------- #
# What it will not reach.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("over", "why"),
    [
        ({"mode": "direct_trap_ring"}, "direct_trap"),
        ({"mode": "threads"}, "mode_cannot_dump"),
        ({"mode": "itinerary"}, "mode_cannot_dump"),
        ({"palette": finished.recipe(mirror=True, phase=0.3)}, "already_rotated"),
        ({"palette": finished.recipe(mirror=True, cycles=2.0)}, "repeated_gradient"),
        ({"curve": "log"}, "curve_override"),
    ],
)
def test_a_recipe_this_pass_cannot_rotate_says_which_member_stops_it(over, why):
    """One reason a row, and the first one wins.

    Each is a fact about the **recipe** and never about the row's quality, which
    is what makes the census of them the thing the next pass is sized off.
    """
    assert rotation.refusal_of(a_row(recipe=a_recipe(**over)), KINDS) == why


def test_a_plain_candidate_row_is_not_refused():
    assert rotation.refusal_of(a_row(), KINDS) is None


def test_a_direct_trap_is_refused_and_is_not_owed():
    """The one refusal that is not a debt.

    `Palette.phase` is a byte-for-byte no-op on a trap figure over a flat ground —
    `engine/src/direct_trap.rs` on purpose, measured 2026-09-10 at eleven varied
    tiles to one sha256 — so there is no rotation of one to come back for. Every
    other refusal is a row some renderer could rotate at full price, and [`owed`]
    is the difference.
    """
    refused = {name: 0 for name in rotation.REFUSALS}
    refused["direct_trap"] = 287
    refused["mode_cannot_dump"] = 1915
    assert rotation.owed(refused) == {"mode_cannot_dump": 1915}


@pytest.mark.parametrize("mode", ["threads", "itinerary"])
def test_the_owed_arm_takes_the_rows_whose_mode_cannot_dump(mode):
    """The one refusal that is a PRICE and not a fact about the picture, so the one
    the flag may lift. `colorize.render` already renders these — a mode with no
    field to dump falls through to the render path — so what `--owed` buys is six
    iteration passes a row against a dumpable row's one, and nothing else moves."""
    row = a_row(recipe=a_recipe(mode=mode))
    assert rotation.refusal_of(row, KINDS) == "mode_cannot_dump"
    assert rotation.refusal_of(row, KINDS, owed=True) is None


@pytest.mark.parametrize("mode", ["smooth", "stripe"])
def test_the_two_arms_partition_the_passing_set_rather_than_overlapping(mode):
    """Swapped and not widened. The two are priced an order apart — six iteration
    passes a row against one — so an arm holding both would report one
    seconds-a-row over two prices, and would re-run the cheap half nobody asked
    for: a dumpable row's four losers were freed rather than merged, so the dedupe
    does not stop it."""
    row = a_row(recipe=a_recipe(mode=mode))
    assert rotation.refusal_of(row, KINDS) is None
    assert rotation.refusal_of(row, KINDS, owed=True) == "dumpable_not_owed"


def test_the_other_arms_work_is_not_counted_as_a_debt():
    refused = dict.fromkeys(rotation.REFUSALS, 0)
    refused["dumpable_not_owed"] = 6036
    refused["direct_trap"] = 299
    refused["already_rotated"] = 3632
    assert rotation.owed(refused) == {"already_rotated": 3632}


def test_a_direct_trap_stays_refused_under_the_owed_arm():
    """A debt the owed arm does not take, because it is not a debt: `phase` is a
    byte-for-byte no-op on a trap figure over a flat ground, so there is no
    rotation of one for a full-price pass to go and get."""
    row = a_row(recipe=a_recipe(mode="direct_trap_ring"))
    assert rotation.refusal_of(row, KINDS, owed=True) == "direct_trap"


@pytest.mark.parametrize(
    ("over", "why"),
    [
        ({"palette": finished.recipe(mirror=True, phase=0.3)}, "already_rotated"),
        ({"curve": "log"}, "curve_override"),
    ],
)
def test_the_owed_arm_lifts_one_refusal_and_not_the_others(over, why):
    """It is not a `--force`. Every other refusal is a fact about the recipe that a
    full-price render does not change."""
    row = a_row(recipe=a_recipe(mode="threads", **over))
    assert rotation.refusal_of(row, KINDS, owed=True) == why


def test_every_refusal_the_census_counts_is_one_this_module_can_produce():
    """A reason in the tuple that nothing returns would be a column of zeroes
    nobody could act on, and a reason returned that is not in the tuple would be a
    `KeyError` in the middle of a population read."""
    produced = {
        rotation.refusal_of(a_row(recipe=a_recipe(**over)), KINDS)
        for over in (
            {"mode": "direct_trap_ring"},
            {"mode": "threads"},
            {"palette": finished.recipe(mirror=True, phase=0.3)},
            {"palette": finished.recipe(mirror=True, cycles=2.0)},
            {"curve": "log"},
            {"mode_params": {"opacity": 0.6}},
        )
    }
    assert produced <= set(rotation.REFUSALS)
    # **Both arms, and every name reached.** One refusal is only ever produced on
    # the owed arm and one only ever off it, so a sweep over one of them would
    # leave a name in the tuple that nothing returns.
    both = produced | {
        rotation.refusal_of(a_row(recipe=a_recipe(mode=mode)), KINDS, owed=True)
        for mode in ("smooth", "threads", "direct_trap_ring")
    }
    # `off_candidate_regime` and `no_picture` are asked of the row and not of the
    # recipe, and are the two lines below; `key_does_not_reproduce` is `_resolve`'s
    # and is the one name here no population read can return.
    assert set(rotation.REFUSALS) - both == {
        "off_candidate_regime",
        "no_picture",
        "key_does_not_reproduce",
    }
    assert rotation.refusal_of(a_row(at_candidate_regime=False), KINDS) == "off_candidate_regime"
    assert rotation.refusal_of(a_row(picture=None), KINDS) == "no_picture"


# --------------------------------------------------------------------------- #
# What it will not remove.
# --------------------------------------------------------------------------- #
def test_a_row_is_held_by_exactly_one_reason_and_always_the_same_one():
    """Two reasons holding one row must count once, or the census adds up to the
    reasons rather than to the rows. First one wins, in `RETAINED_REASONS`' order."""
    held = {
        store_module.RETAINED_SEATED: {("leg", "00001")},
        store_module.RETAINED_LABELED: set(),
        store_module.RETAINED_FITTED: {"k0"},
        store_module.RETAINED_TENTATIVE: {"k0"},
    }
    assert rotation.holder_of(a_row(), held) == store_module.RETAINED_SEATED
    held[store_module.RETAINED_SEATED] = set()
    assert rotation.holder_of(a_row(), held) == store_module.RETAINED_FITTED
    held[store_module.RETAINED_FITTED] = set()
    assert rotation.holder_of(a_row(), held) == store_module.RETAINED_TENTATIVE
    held[store_module.RETAINED_TENTATIVE] = set()
    assert rotation.holder_of(a_row(), held) is None
    assert (
        rotation.holder_of(a_row(rejected={"by": "matt"}), held) == store_module.RETAINED_REJECTED
    )


def test_a_seat_reached_through_also_recorded_holds_the_row():
    """A picture is one picture and a pass writes two decisions about it — a gate
    row for the attempt and a release row for the seat. A protection that read
    only `provenance` would miss the second and take a released wallpaper."""
    held = {
        store_module.RETAINED_SEATED: {("gallery9", "00031")},
        store_module.RETAINED_LABELED: set(),
        store_module.RETAINED_FITTED: set(),
        store_module.RETAINED_TENTATIVE: set(),
    }
    row = a_row(
        provenance={
            "run": "leg",
            "candidate": "00001",
            "also_recorded": [{"run": "gallery9", "candidate": "00031"}],
        }
    )
    assert rotation.holder_of(row, held) == store_module.RETAINED_SEATED


def test_the_pass_honours_every_protection_the_prune_does():
    """The prompt names two and this honours five, which is the safe direction:
    a pass that protects more rows than it was asked to cannot take one it should
    have kept. The guard is that the two lists are the same list."""
    assert set(rotation.protections(log=lambda *_a: None)) | {
        store_module.RETAINED_REJECTED
    } == set(store_module.RETAINED_REASONS[1:])


# --------------------------------------------------------------------------- #
# The decision.
# --------------------------------------------------------------------------- #
def a_candidate(key, p_fine, phase=0.5):
    return {"key": key, "phase": phase, "p_fine": p_fine, "p_coarse": 0.5, "index": 0}


def test_the_incumbent_keeps_its_place_when_no_rotation_beats_it():
    verdict = rotation.decide(
        {"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.5, "held_by": None},
        [a_candidate("r1", 0.4), a_candidate("r2", 0.49)],
    )
    assert verdict == {"verdict": rotation.KEPT, "winner": "k0", "adopt": None, "remove": None}


def test_a_winning_rotation_replaces_the_row_it_rotated():
    verdict = rotation.decide(
        {"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.5, "held_by": None},
        [a_candidate("r1", 0.4), a_candidate("r2", 0.7)],
    )
    assert verdict == {
        "verdict": rotation.ADOPTED,
        "winner": "r2",
        "adopt": "r2",
        "remove": "k0",
    }


def test_a_held_rows_winner_is_adopted_and_the_row_stays():
    """⚠ The prompt's own sentence: *if a labelled row's rotation wins, keep both*.

    A guard refuses the **removal** and never the adoption — a rotation that beats
    a labelled row is a picture worth having, and the label is a fact about the
    other one.
    """
    verdict = rotation.decide(
        {"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.5, "held_by": "a_label_row_joins_to_it"},
        [a_candidate("r1", 0.9)],
    )
    assert verdict == {"verdict": rotation.HELD, "winner": "r1", "adopt": "r1", "remove": None}


def test_the_tolerance_is_read_against_the_stored_column_and_not_the_fresh_one():
    """The only reading that can refuse anything.

    A rotation winning best-of-six has beaten the incumbent's *fresh* score by
    construction, so a factor on that would refuse nothing ever. Against the
    stored column it catches the six of them coming in far under what the store
    says the row is worth — which is a levelling, a head or a picture that moved,
    and is a thing to notice rather than a thing to adopt.
    """
    incumbent = {"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.10, "held_by": None}
    refused = rotation.decide(incumbent, [a_candidate("r1", 0.20)], tolerance=0.9)
    assert refused["verdict"] == rotation.REFUSED_BY_TOLERANCE
    assert refused["adopt"] is None and refused["remove"] is None
    taken = rotation.decide(incumbent, [a_candidate("r1", 0.46)], tolerance=0.9)
    assert taken["verdict"] == rotation.ADOPTED


def test_a_row_whose_rotations_all_failed_decides_nothing():
    """`nothing_made` and not `kept`: the two are different facts, and a pass that
    reported a failed render as the incumbent winning would be claiming a
    comparison it never made."""
    verdict = rotation.decide({"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.5}, [])
    assert verdict["verdict"] == rotation.NOTHING_MADE
    assert verdict["winner"] is None


def test_an_unreadable_incumbent_still_lets_the_rotations_compete():
    """`p_fine` of `None` on the incumbent is a picture the head could not read,
    and the six are then five. The tolerance still runs, because the **stored**
    column is what it reads and that is on the row rather than on the picture."""
    verdict = rotation.decide(
        {"key": "k0", "stored_p_fine": 0.5, "p_fine": None, "held_by": None},
        [a_candidate("r1", 0.8)],
    )
    assert verdict["verdict"] == rotation.ADOPTED


def test_every_verdict_the_counter_holds_is_one_decide_can_return():
    """A verdict `decide` returns that `VERDICTS` does not hold is a `KeyError` in
    the middle of a chunk; one in `VERDICTS` that nothing returns is a column of
    zeroes on every record this pass will ever write."""
    incumbent = {"key": "k0", "stored_p_fine": 0.5, "p_fine": 0.5, "held_by": None}
    seen = {
        rotation.decide(incumbent, [])["verdict"],
        rotation.decide(incumbent, [a_candidate("r", 0.1)])["verdict"],
        rotation.decide(incumbent, [a_candidate("r", 0.9)])["verdict"],
        rotation.decide({**incumbent, "held_by": "x"}, [a_candidate("r", 0.9)])["verdict"],
        rotation.decide({**incumbent, "p_fine": 0.0}, [a_candidate("r", 0.01)])["verdict"],
    }
    assert seen == set(rotation.VERDICTS)


# --------------------------------------------------------------------------- #
# The removal transaction.
# --------------------------------------------------------------------------- #
@pytest.fixture
def a_store(tmp_path, monkeypatch):
    """The ledger's three files in a temporary directory, and nothing else touched.

    Redirected at the **tier roots**, which is `test_candidate_ledger.isolated`'s
    rule and the reason it is a rule: `sweep.remove` rewrites all three files
    against one set of keys and refuses outright if they are not in one directory,
    so a fixture that moved two of them would either be refused or rewrite this
    machine's real store.
    """
    from fractal_wallpapers import paths
    from fractal_wallpapers.curation import flatness

    root = tmp_path / "artifacts"
    (root / "curation").mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    where = root / "curation" / store_module.UNIT
    where.mkdir(parents=True)
    monkeypatch.setattr(flatness, "sidecar_path", lambda: where / flatness.SIDECAR_NAME)
    monkeypatch.setattr(ratchet, "log_path", lambda: tmp_path / "ratchet.jsonl")

    rows = [a_row(key="k0"), a_row(key="k1"), a_row(key="k2")]
    for key in ("k0", "k1", "k2"):
        picture = root / "curation" / "depth" / "leg" / "pictures" / f"{key}.jpg"
        picture.parent.mkdir(parents=True, exist_ok=True)
        picture.write_bytes(b"not really a jpeg")
        (picture.parent / f"{key}.leveled").mkdir(exist_ok=True)
        (picture.parent / f"{key}.leveled" / "map.json").write_text("{}", encoding="utf-8")
    _write(store_module.rows_path(), rows)
    _write(
        store_module.scores_path(),
        [{"schema": 1, "key": f"{key}|a|b", "recipe_key": key} for key in ("k0", "k1", "k2")],
    )
    _write(
        flatness.sidecar_path(),
        [{"schema": 1, "recipe_key": key, "flat16_1.0": 0.1} for key in ("k0", "k1", "k2")],
    )
    return root


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _keys(path, column="key"):
    return [
        json.loads(line)[column]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_a_removal_takes_the_row_out_of_all_three_files(a_store):
    """The sidecars go with the row or they are rows nothing joins to.

    One transaction and one set of keys: the ledger row, its score sidecar row and
    its flatness column. A removal that took the row alone would leave a `p_ge4`
    and a rank feature keyed on a recipe the store no longer holds.
    """
    from fractal_wallpapers.curation import flatness

    record = sweep.remove(["k1"], why="test")
    assert record["in_the_store"] == 1 and record["not_in_the_store"] == 0
    assert _keys(store_module.rows_path()) == ["k0", "k2"]
    assert _keys(store_module.scores_path(), "recipe_key") == ["k0", "k2"]
    assert _keys(flatness.sidecar_path(), "recipe_key") == ["k0", "k2"]


def test_a_removal_takes_the_picture_and_its_levelled_colormap(a_store):
    """A levelled colormap outliving its picture is how 206,147 of them reached
    14.9 GiB. It is swept with the picture, and the argument is sound here for
    `delete_pictures`' own reason: the row goes in the same transaction, so
    nothing can name the candidate again."""
    sweep.remove(["k1"], why="test")
    pictures = a_store / "curation" / "depth" / "leg" / "pictures"
    assert not (pictures / "k1.jpg").exists()
    assert not (pictures / "k1.leveled").exists()
    assert (pictures / "k0.jpg").is_file()
    assert (pictures / "k0.leveled").is_dir()


def test_a_removal_writes_its_loss_down_so_the_ratchet_can_forgive_it(a_store):
    """The property the single-deletion-site rule was protecting, kept rather than
    spent. A row that left this store with no transaction accounting for it is
    exactly what `test_leveled_identity`'s census is a ratchet in order to catch.
    """
    sweep.remove(["k1", "k2"], why="rotation/pass")
    entries = ratchet.entries()
    assert [row["event"] for row in entries] == [ratchet.DELETED]
    assert entries[0]["why"] == "rotation/pass"
    assert entries[0]["counts"]["rows"] == 2
    assert ratchet.reading()["deleted"]["rows"] == 2


def test_a_removal_marks_nothing_because_it_only_ever_shrinks(a_store):
    """A mark is a claim that the store *reached* a size, and this transaction
    cannot grow it. A removal that advanced the mark would be the census forgiving
    a loss nobody took."""
    sweep.remove(["k1"], why="test")
    assert ratchet.reading()["mark"] == {}


def test_a_dry_removal_reads_and_touches_nothing(a_store):
    record = sweep.remove(["k1"], why="test", apply=False)
    assert record["applied"] is False
    assert record["pictures"] == {"would_delete": 1}
    assert _keys(store_module.rows_path()) == ["k0", "k1", "k2"]
    assert ratchet.entries() == []


def test_a_removal_naming_no_key_is_refused_rather_than_a_no_op(a_store):
    """An empty key set is a caller that resolved nothing, and the safe reading of
    it is *something upstream is wrong* rather than *take nothing*."""
    with pytest.raises(candidate_ledger.LedgerError):
        sweep.remove([], why="test")


def test_a_key_the_store_does_not_hold_is_counted_and_not_an_error(a_store):
    """The ordinary state of a pass re-merged after a prune already took the row."""
    record = sweep.remove(["k1", "nowhere"], why="test")
    assert record["in_the_store"] == 1
    assert record["not_in_the_store"] == 1
    assert _keys(store_module.rows_path()) == ["k0", "k2"]


# --------------------------------------------------------------------------- #
# The mining arm's draw.
# --------------------------------------------------------------------------- #
def a_shot(mode="smooth", colormap="magma", place="p0"):
    from fractal_wallpapers.curation import depth

    return depth.Shot(
        arm="ranked_bands",
        location=place,
        partition="mandelbrot",
        mode=mode,
        colormap=colormap,
        k=1,
        band="b3",
        rank=17,
        rank_fraction=0.02,
    )


def test_a_mined_shot_is_its_own_phase_zero_plus_the_rotations():
    """The control is the candidate a leg with no rotations on the table would
    have made — same place, same mode, same map, the plain palette pass.

    A best-of-five over a candidate nobody would have drawn is a number about
    nothing, so `k=0` carries no palette override at all and takes the plain
    candidate key. That is also what makes the row readable against the rest of
    the pool: it is the same recipe the unvaried leg would have written.
    """
    made = rotation.drawn_rotations(a_shot(), seed=11)
    assert len(made) == rotation.MINE_ROTATIONS + 1
    assert [one.k for one in made] == [0, 1, 2, 3, 4]
    assert made[0].palette == {} and made[0].phase == 0.0
    assert all(set(one.palette) == {"phase"} for one in made[1:])
    assert len({one.phase for one in made}) == len(made)


def test_a_direct_trap_is_drawn_bare_and_takes_no_second_key():
    """⚠ `Palette.phase` is a byte-for-byte no-op on a trap figure over a flat
    ground. A rotation there would take a second recipe key for the same picture
    and put a duplicate in the pool under a name claiming it was varied."""
    made = rotation.drawn_rotations(a_shot(mode="direct_trap_ring"), seed=11)
    assert [one.k for one in made] == [0]
    assert made[0].palette == {}


def test_a_mined_shots_phases_are_seeded_off_the_shot_and_not_the_stream():
    """Same reason as the store arm's: a plan truncated at the clock and a plan
    re-run must ask the same questions of the same shots, whatever came before."""
    first = [one.phase for one in rotation.drawn_rotations(a_shot(), seed=5)]
    assert first == [one.phase for one in rotation.drawn_rotations(a_shot(), seed=5)]
    assert first != [
        one.phase for one in rotation.drawn_rotations(a_shot(colormap="viridis"), seed=5)
    ]
    assert first != [one.phase for one in rotation.drawn_rotations(a_shot(mode="stripe"), seed=5)]
    assert first != [one.phase for one in rotation.drawn_rotations(a_shot(place="p1"), seed=5)]


def test_a_resumed_leg_takes_a_slice_of_the_whole_plan_and_not_a_smaller_plan():
    """The two halves of a clock-bound leg are one leg or they are not comparable.

    Re-drawing is not the same act: each shot's four losers are recorded and
    **freed** rather than merged, so nothing in the store stops them being made
    again, and a shot whose control never merged comes back as a best-of-four read
    against the same control — a different number under the same name.
    """
    blocks = [[f"block{at}"] for at in range(10)]
    held, skipped = resumed_quietly(blocks, 4)
    assert skipped == 4
    assert held == blocks[4:], "block 4 of the resumed leg is block 4 of the plan"
    assert resumed_quietly(blocks, 0) == (blocks, 0)


def test_a_leg_told_to_resume_past_its_own_plan_has_finished_rather_than_failed():
    blocks = [[f"block{at}"] for at in range(10)]
    assert resumed_quietly(blocks, 10) == ([], 10)
    assert resumed_quietly(blocks, 99) == ([], 10), "clamped, because it is a fact to report"
    assert resumed_quietly(blocks, -3) == (blocks, 0)


def resumed_quietly(blocks, at):
    return rotation.resumed(blocks, at, 14400.0, 3600.0, log=lambda *_a: None)


def test_a_mined_shot_carries_the_arm_and_the_band_it_was_drawn_under():
    """A row that has forgotten which arm and which rank band drew it cannot be in
    the readout a mining leg exists to produce, and `hunt_block` is where a
    `k`-dependent correction reads them back off the ledger."""
    made = rotation.drawn_rotations(a_shot(), seed=11)
    assert {one.arm for one in made} == {"ranked_bands"}
    assert {one.band for one in made} == {"b3"}


def test_the_mining_width_is_prune_free_arithmetic_and_not_a_knob():
    """Twelve modes at width 12 is one map a (location, mode); a best-of-five
    merges one row of the five. One row a pair against a keep of five is what
    makes the merge prune-free, and it is arithmetic rather than a setting."""
    from fractal_wallpapers.curation import mode_policy

    assert len(mode_policy.mined()) == rotation.MINE_WIDTH
    assert candidate_ledger.RETAIN_PER_PAIR >= 1


def test_the_mining_shares_are_spelled_whole_because_build_plan_merges():
    """`depth.build_plan` merges what it is given over `depth.SHARES`, so a table
    naming the ranked share alone leaves the near-band and flat draws on their 0.25
    defaults — and the leg spends half its clock on arms the last producing leg
    zeroed, with its record reporting a share it did not run."""
    from fractal_wallpapers.curation import depth

    assert set(rotation.MINE_SHARES) == set(depth.DRAWS), "every draw, so nothing is inherited"
    assert rotation.MINE_SHARES[depth.RANKED] == 1.0
    merged = {**depth.SHARES, **rotation.MINE_SHARES}
    assert sum(value for arm, value in merged.items() if arm != depth.RANKED) == 0.0
    from fractal_wallpapers.curation import mode_policy

    _shares, _roster, stated = depth.resolve_split(
        rotation.MINE_SHARES, mode_policy.mined(), log=lambda *_a: None
    )
    assert stated["shares_inherited"] == {}, "a whole table inherits nothing to be surprised by"


# --------------------------------------------------------------------------- #
# Resuming a clock-bound mining leg.
# --------------------------------------------------------------------------- #
#: The mined roster, spelled out because the fixture's records are the ones that
#: landed on 2026-09-11 and a record is a record of what a leg was given.
ROSTER = (
    "smooth",
    "tia",
    "stripe",
    "smooth_mean_angle",
    "smooth_angle_min",
    "smooth_stripe",
    "smooth_curvature",
    "direct_trap_screen",
    "direct_trap_multiply",
    "direct_trap_lines",
    "threads",
    "itinerary",
)


@pytest.fixture
def two_legs(tmp_path, monkeypatch):
    """A leg builder over an empty store: `mine_ckpt120`'s shape and its numbers.

    The real ones, from 2026-09-11: a first leg handed four chunks of 400 by the
    pool and cut at its 14,400 s budget with 247 location blocks decided, and a
    second told `--from-block 247` that was handed 400 again and decided 129.
    Redirected at the **tier roots**, which is `a_store`'s rule.

    A record asked for `before_the_protocol` is written **without**
    `plan_budget_seconds`, `from_block`, `shares_asked` or the `conditioned`
    share, because `mine_ckpt120`'s carries none of them: they landed with the
    resume protocol after it ran, and a guard that holds only for records written
    since is a guard that does not hold.
    """
    from fractal_wallpapers import paths

    root = tmp_path / "artifacts"
    (root / "curation").mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")

    def a_leg(name, *, from_block, decided, before_the_protocol=False):
        rotation.rotation_dir(name).mkdir(parents=True)
        with rotation.decisions_path(name).open("w", encoding="utf-8", newline="\n") as handle:
            for at in range(decided):
                # Several shots a location, because a block is the location and
                # `MINE_WIDTH` maps go over the roster at each one: what the
                # index counts is distinct locations and never decision rows.
                for mode in ("smooth", "stripe", "threads"):
                    handle.write(
                        json.dumps(
                            {"schema": 1, "location": f"place{from_block + at}", "mode": mode}
                        )
                        + "\n"
                    )
        record = {
            "schema": 1,
            "name": name,
            "arm": "mine",
            "seed": 0,
            "roster": list(ROSTER),
            "shares": {"ranked_bands": 1.0, "flat": 0.0, "near_band": 0.0, "mode_floor": 0.0},
            "width": 12,
            "plan": {
                "rate_seconds": 6.0,
                "budget_seconds": 14400.0,
                "width": 12,
                "workers_sized_for": 3,
            },
            "counts": {
                "blocks_planned": 960,
                "blocks_skipped": from_block,
                "blocks_done": 400,
                "blocks_decided": decided,
            },
        }
        if not before_the_protocol:
            record["plan_budget_seconds"] = 14400.0
            record["from_block"] = from_block
            record["shares"]["conditioned"] = 0.0
            record["resume_from_block"] = from_block + decided
        rotation.record_path(name).write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        return record

    return a_leg


def the_plan(**over):
    """The flags `mine_ckpt120` ran, which is what a resume of it has to restate."""
    return {
        "seed": 0,
        "rate": 6.0,
        "plan_budget": 14400.0,
        "width": 12,
        "workers": 3,
        "roster": list(ROSTER),
        "shares": dict(rotation.MINE_SHARES),
        **over,
    }


def quietly(at, **over):
    return rotation.refuse_unreachable_resume(at, log=lambda *_a: None, **the_plan(**over))


def test_the_recorded_resume_index_is_the_locations_the_leg_actually_decided(two_legs):
    """⚠ The record's own claim held against its own file, which is the point.

    `blocks_done` is incremented by the whole chunk once the pool returns while
    each worker breaks out of its block list at the deadline, so it rounds up to
    `CHUNK_GROUPS`: `mine_ckpt120` recorded 400 and had decided 247. Passing that
    400 to `--from-block` would have discarded 153 rendered locations, about 1,836
    shots. So `resume_from_block` is pinned to a **re-read of the decisions**, and
    pinned against the arithmetic it is not.
    """
    first = two_legs("mine_ckpt120", from_block=0, decided=247, before_the_protocol=True)
    assert rotation.decided_blocks("mine_ckpt120") == 247
    assert rotation.resume_index("mine_ckpt120") == 247
    handed = first["counts"]["blocks_skipped"] + first["counts"]["blocks_done"]
    assert handed == 400, "what the pool was handed, which is what blocks_done means"
    assert rotation.resume_index("mine_ckpt120") != handed

    # The resumed half. `--from-block` indexes the WHOLE plan while this leg's own
    # decisions file holds only its own 129, so the index is both halves.
    second = two_legs("m2", from_block=247, decided=129)
    assert rotation.decided_blocks("m2") == 129
    assert rotation.resume_index("m2") == 376
    assert second["resume_from_block"] == rotation.resume_index("m2")
    assert second["counts"]["blocks_skipped"] + second["counts"]["blocks_done"] == 647


def test_a_leg_that_decided_nothing_resumes_where_it_was_told_to_start(two_legs):
    """A leg killed before its first chunk came back has rendered nothing, so the
    index to continue it at is the one it was given — never the blocks the pool
    was holding when it died."""
    two_legs("killed", from_block=376, decided=0)
    assert rotation.decided_blocks("killed") == 0
    assert rotation.resume_index("killed") == 376


def test_a_from_block_above_what_this_plan_rendered_is_refused_at_start_up(two_legs):
    """Passing one **always** discards work that was paid for, so it is an error.

    Four hours in is the wrong place to find that out: this runs before the
    population read, which is a minute on its own, and before any render at all.
    400 is what `blocks_done` gives against the 376 two legs between them reached.
    """
    two_legs("mine_ckpt120", from_block=0, decided=247, before_the_protocol=True)
    two_legs("m2", from_block=247, decided=129)
    with pytest.raises(rotation.RotationRefused, match="above the 376"):
        quietly(400)
    # `blocks_skipped + blocks_done` — the arithmetic the record's own fields
    # invite and the one the report had to talk the next leg out of.
    with pytest.raises(rotation.RotationRefused, match="647"):
        quietly(647)
    held = quietly(376)
    assert held == {"mine_ckpt120": 247, "m2": 376}
    assert quietly(247) == held, "the first leg's own index is still reachable"


def test_a_first_leg_is_asked_nothing_because_it_continues_nothing(two_legs):
    assert quietly(0) == {}
    assert quietly(-1) == {}


def test_a_resume_that_would_rebuild_a_different_plan_is_refused_rather_than_run(two_legs):
    """★ `overnight_ckpt121`'s finding, made mechanical. The plan is
    `PLAN_HEADROOM * workers * plan_budget / rate`, so a resume that leaves
    `--rate` on `MINE_RATE` while the first leg ran at 6.0 plans 27,648 shots
    against 11,520 and then skips 247 blocks of a draw nobody has rendered."""
    two_legs("mine_ckpt120", from_block=0, decided=247, before_the_protocol=True)
    for over in (
        {"rate": rotation.MINE_RATE},
        {"plan_budget": 8000.0},
        {"seed": 1},
        {"width": 8},
        {"workers": 2},
        {"roster": list(ROSTER[:3])},
        {"shares": {**rotation.MINE_SHARES, "flat": 0.25}},
    ):
        with pytest.raises(rotation.RotationRefused, match="no mine leg on record ran"):
            quietly(247, **over)


def test_a_zero_share_added_after_a_leg_ran_does_not_unmake_its_resume(two_legs):
    """⚠ The resolved share table grows a key whenever a draw joins `depth.DRAWS`
    — `conditioned` landed between these two legs — so an identity over the table
    whole would refuse a legitimate resume over an arm neither leg spent a second
    of clock on. Only the arms carrying a share are part of it.
    """
    first = two_legs("mine_ckpt120", from_block=0, decided=247, before_the_protocol=True)
    second = two_legs("m2", from_block=247, decided=129)
    assert set(first["shares"]) != set(second["shares"]), "the fixture is the real shape"
    assert rotation.identity_of(first) == rotation.identity_of(second)
    assert rotation.identity_of(first) == rotation.plan_identity(**the_plan())


def test_only_a_mine_legs_record_is_offered_to_a_mine_resume(two_legs):
    """The store arm keeps its records in the same subtree and takes no resume
    index at all — its figure is `rows_remaining` — so an `arm` that is not
    `mine` is not a half of a block plan however well its plan block matches."""
    two_legs("mine_ckpt120", from_block=0, decided=247, before_the_protocol=True)
    record = json.loads(rotation.record_path("mine_ckpt120").read_text(encoding="utf-8"))
    rotation.record_path("mine_ckpt120").write_text(
        json.dumps({**record, "arm": "store"}, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(rotation.RotationRefused, match="no mine leg on record ran"):
        quietly(247)
