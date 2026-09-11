"""That a graded picture cannot be pruned out from under the store that judged it.

The `gallery_grade` corpus is the population a conditional head is fitted on, and
the half of it that matters most is the half the rank drops. Its first sitting is
700 seated rows and **300 runners-up** — near neighbours the solve refused, which
are exactly the hard negatives a head learning an order inside the gate's own top
has to be shown. The seated rows are held by
[`curation.tentative.protected_keys`], because the record they were drawn from
names them. The runners-up are named by no record at all: measured 2026-09-06,
**233 of the 300 were held by nothing, 95 of those carrying a `<stem>.leveled/`
colormap**, and a `.leveled/` dies with the picture it sits beside. Retention is
not retroactive, so one merge before the head was fit would have taken them for
good.

The protection is [`candidate_ledger.RETAINED_LABELED`] and no new class beside
it — a grade is a person's verdict about a picture, keyed through the same
[`labeling.finished.render_key`] the two gates' verdicts are, so
[`curation.retention.labeled_renders`] reads this store too. What is pinned here
is that it does, and that the join lands where it has to.

## Two halves, failing on different things

* **The protection is applied**, behaviourally — a ledger row the rank drops at
  K=1 survives a `prune` because a grade names it, and it survives *as*
  `RETAINED_LABELED`. Fast, synthetic, no ledger. It fails the day the reader is
  narrowed back to the two gates.
* **It reaches the real store**, over the tracked rows and this machine's ledger.
  The claim is per row and not per count: every graded row's drawn candidate is a
  ledger row the protection marks, its picture is on disk, and where the row says
  `leveled` the directory beside that picture is there.

## What a plan is doing in a retention guard

A row carries `leveled` as a boolean and never a path, so the store cannot say
which directory a picture went through. `gallery_grade.plan_paths()` can, and
those files are the only thing that can rebuild a levelled picture as it was
judged — the sheets' rendered pictures are regenerable and the plans are not.
A protection that kept every colormap and lost the plans would keep the bytes and
lose the ability to name them.

**The reading this was written against**, 2026-09-06, over the ledger the ckpt-112
mine left: 1,000 graded rows over 815 locations, 1,000 distinct drawn candidates,
all 1,000 found among the ledger's **308,419** rows, all 1,000 pictures on disk,
**373** levelled directories present, and each graded render key carried by
**exactly one** ledger row — the candidate the draw named. That last is not
asserted: a later leg re-rendering one of these recipes at another regime would
put a second row on the key, and both would be protected, which is the harmless
direction. What is asserted is the direction that is not harmless — that the
drawn candidate itself is reached.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_candidate_ledger import decision, isolated  # noqa: F401  (a fixture)

from fractal_wallpapers.curation import candidate_ledger, recipes, retention
from fractal_wallpapers.labeling import finished, gallery_grade, store
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.paths import Tiers, rehome


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


@pytest.fixture
def grade_store(tmp_path, monkeypatch):
    """This store's tracked records in `tmp_path`, with one batch registered.

    `repo_root` and not `store_dir`, because the module builds both its paths off
    the one call and patching the deeper of the two would leave the registry on
    this machine — where a synthetic batch would then be appended to a tracked
    file.
    """
    monkeypatch.setattr(gallery_grade, "repo_root", lambda: tmp_path)
    gallery_grade.register(
        registry_module.Registration(
            batch="a_batch", method="the seats of one record, and rows it refused"
        )
    )
    return tmp_path / "data" / gallery_grade.NAME


def grade_of(recipe: dict, *, grade: int = 4, **over) -> dict:
    """A gallery-grade row built off a **stored ledger recipe**, so the two keys agree.

    The join under test is `render_key`, and a row typed out by hand here would be
    testing that two literals match rather than that the join does.
    """
    fields = {
        "batch": "a_batch",
        "grade": grade,
        "family": recipe["family"],
        "viewport": recipe["viewport"],
        "mode": recipe["mode"],
        "mode_params": dict(recipe.get("mode_params") or {}),
        "curve": recipe["curve"],
        "colormap": recipe["colormap"],
        "recipe_": recipe["palette"],
        "render": {
            "resolution": [1280, 720],
            "supersample": 2,
            "maxiter": int(recipe["maxiter"]),
            "filter": "lanczos3",
        },
        "labeler": "matt",
    }
    fields.update(over)
    return gallery_grade.grade_row(**fields)


def two_rows_one_pair() -> list[dict]:
    """Two ledger rows at one place and one mode, differing only in their colormap.

    One pair, so `K=1` keeps one of them; both unscored, so [`retention.decide`]
    ranks them last within the pair and breaks the tie on the key — which makes
    `k1` the row the rank drops and therefore the row worth grading.
    """
    out = []
    for key, colormap in (("k0", "magma"), ("k1", "viridis")):
        source = decision(candidate=key)
        source["recipe"] = {**source["recipe"], "colormap": colormap}
        out.append(
            candidate_ledger.row(
                recipe=recipes.of_decision(source),
                key=key,
                source={**source, "_store": candidate_ledger.FROM_GALLERY},
                picture=f"artifacts/curation/depth/a_leg/pictures/{key}.jpg",
            )
        )
    return out


# --------------------------------------------------------------------------- #
# The protection is applied, and it is the label class that applies it.
# --------------------------------------------------------------------------- #
def test_a_human_grade_is_a_label_the_retention_reads(grade_store) -> None:
    """One call, three claims, because the reader costs a pass of every label store.

    A person's grade marks its render; a rule's does not — a derivation this
    project can run again is not a judgement that would be lost with the picture,
    which is the distinction the label store keeps in the first place. And the two
    gates are still read, so a reader narrowed to this store alone fails here
    rather than quietly stopping protecting everything it used to.
    """
    rows = two_rows_one_pair()
    kept = recipes.of_record(rows[0]["recipe"])
    dropped = recipes.of_record(rows[1]["recipe"])
    gallery_grade.append([grade_of(rows[0]["recipe"])])
    gallery_grade.append([grade_of(rows[1]["recipe"], origin=f"{store.RULE_PREFIX}a_rule")])

    marked = retention.labeled_renders()

    assert retention.render_key_of(rows[0]) in marked, "a human grade did not mark its render"
    assert retention.render_key_of(rows[1]) not in marked, (
        "a rule-written grade marked a render; a derivation is not a judgement"
    )
    assert marked - {retention.render_key_of(rows[0])}, (
        "the two finished heads' human rows are no longer read, so this reader has "
        "stopped protecting everything it used to protect"
    )
    # Spelled off the recipes so a failure says which picture, not which tuple.
    assert kept.colormap != dropped.colormap


def test_the_prune_keeps_a_graded_candidate_the_rank_would_have_dropped(
    isolated,  # noqa: F811
    grade_store,
) -> None:
    """**The guard the store rests on.** A runner-up is a row the solve refused
    and the rank has no reason to keep, and it is the half of this corpus a head
    is fitted to separate. Without the protection it goes in the next merge, with
    its picture and its levelled colormap, and nothing says so.

    One prune and not a before-and-after: `saved_by_a_protection` is already the
    counterfactual — it counts protected keys whose *rank* verdict was not
    `RANKED`, so a 1 there is the rank dropping this row and the grade keeping it,
    in one number.
    """
    rows = two_rows_one_pair()
    candidate_ledger.write(rows)
    gallery_grade.append([grade_of(rows[1]["recipe"])])

    kept = candidate_ledger.prune(keep=1, apply=True, log=quiet)

    assert kept["rows_kept"] == 2, "a graded candidate the rank dropped was not protected"
    assert kept["kept_because"][candidate_ledger.RETAINED_LABELED] == 1
    assert kept["saved_by_a_protection"][candidate_ledger.RETAINED_LABELED] == 1, (
        "the rank did not drop this row, so the protection was never the reason it stayed"
    )
    assert kept["pictures"] == {**kept["pictures"], "asked": 0, "deleted": 0}
    assert {row["key"] for row in candidate_ledger.read()} == {"k0", "k1"}


def test_the_protection_is_wired_into_the_prune_and_not_only_declared() -> None:
    """The reader and the class it fills are in two modules, and a `labeled_renders`
    that stopped reading this store would go on reading, on the prune's own record,
    as the label protection running over the right number of stores."""
    import inspect

    body = inspect.getsource(retention.labeled_renders)
    assert "gallery_grade.read()" in body
    assert "finished.HEADS" in body
    assert "retention.labeled_renders()" in inspect.getsource(candidate_ledger._prune_protections)


# --------------------------------------------------------------------------- #
# It reaches the real store.
# --------------------------------------------------------------------------- #
def graded_by_candidate() -> tuple[dict[str, dict], list[dict]]:
    """`({the candidate the draw named: its graded row}, the rows that name none)`.

    **Two populations and not one.** Most graded rows are verdicts about a
    candidate the seating pool drew, and everything below is about those: the
    ledger still holds the row, a label protection marks it, its picture is on
    disk. A minority were never candidates — `p_fine_correction_20260909`'s
    `low_anchor` block is coarse-3 verdicts about 1280x720 pictures pulled from
    the finished-render corpus to anchor the sheet's scale, and
    `models/gallery_grade_train.py`'s `gate_column_is` says the same thing from
    the training side. They have no ledger row to protect and their pictures are
    the coarse store's, which `retention.labeled_renders` protects through
    `finished.HEADS`.

    They were one population until 2026-09-10, keyed on `str(candidate)` — so all
    of them collapsed onto the single key `"None"`, which is how a hundred rows
    hid inside one dictionary entry and why the guard below read them as one row
    naming no candidate.
    """
    drawn: dict[str, dict] = {}
    anchors: list[dict] = []
    for row in gallery_grade.resolved().graded():
        candidate = (row.get("selected_on") or {}).get("candidate")
        if candidate is None:
            anchors.append(row)
        else:
            drawn[str(candidate)] = row
    return drawn, anchors


@pytest.mark.slow
def test_every_graded_row_is_protected_on_the_real_store(tracked_ledger) -> None:
    """Per row and never per count: each graded row's drawn candidate is a ledger
    row the label protection marks, its picture is on disk, and where the row says
    `leveled` the directory beside that picture is there.

    The ledger reading is the session's — see `conftest.tracked_ledger` — so what
    this costs on top of it is one pass of the label stores and a stat per graded
    row.
    """
    drawn, anchors = graded_by_candidate()
    if not drawn:
        pytest.skip("this machine holds no gallery grades")

    # A row that names no candidate has to SAY what it is instead, and the one
    # thing it may be is an anchor drawn from a coarse label batch. That keeps the
    # guard's teeth on the case it was written for — a row whose candidate went
    # missing — while letting through the case it was written before.
    unaccounted = [
        f"{row.get('sheet')}/{row.get('unit')}"
        for row in anchors
        if not (row.get("selected_on") or {}).get("coarse_batch")
    ]
    assert not unaccounted, (
        f"{len(unaccounted)} graded rows name neither a drawn candidate nor the coarse batch "
        f"they were anchored from, so nothing can say which picture they were cast on: "
        f"{unaccounted[:5]}"
    )

    marked = retention.labeled_renders()
    by_key = {str(row["key"]): row for row in tracked_ledger.rows}
    absent = sorted(key for key in drawn if key not in by_key)
    assert not absent, (
        f"{len(absent)} of {len(drawn)} graded rows name a candidate the ledger no longer "
        f"holds, so the picture they were cast on has already been pruned: {absent[:5]}"
    )
    unmarked = sorted(key for key in drawn if retention.render_key_of(by_key[key]) not in marked)
    assert not unmarked, (
        f"{len(unmarked)} of {len(drawn)} graded rows name a candidate no label protection "
        f"reaches, so the next merge takes it with its picture: {unmarked[:5]}"
    )

    tiers = Tiers.current()
    missing_picture: list[str] = []
    missing_colormap: list[str] = []
    for key, row in drawn.items():
        where = rehome(by_key[key].get("picture"), tiers)
        if where is None or not Path(where).is_file():
            missing_picture.append(key)
            continue
        if row.get("leveled") and not (Path(where).parent / f"{Path(where).stem}.leveled").is_dir():
            missing_colormap.append(key)
    assert not missing_picture, (
        f"{len(missing_picture)} graded rows resolve no picture on disk: {missing_picture[:5]}"
    )
    assert not missing_colormap, (
        f"{len(missing_colormap)} graded rows were judged through a `.leveled/` colormap that "
        f"is no longer beside their picture, so a rebuild would serve a different picture "
        f"under the same identity: {missing_colormap[:5]}"
    )


def test_the_plans_that_name_the_levelled_colormaps_are_still_there() -> None:
    """A row carries `leveled` as a boolean, so the plan is the only thing that
    names the directory. Losing these keeps the pictures and loses the ability to
    say which colouring any of them was judged through.

    Off the store's own accessor and not a path spelled here, because
    `tests/test_gallery_grade.py`'s addressing guard is about exactly that.

    The anchor rows are not asked about: a row that named no candidate used to key
    as `"None"` on both sides of this join and match itself, which was an agreement
    about nothing. An anchor's picture comes from the coarse corpus and was never
    cut from one of these plans.
    """
    drawn, _anchors = graded_by_candidate()
    plans = gallery_grade.plan_paths()
    if not drawn or not plans:
        pytest.skip("this machine holds no gallery grades, or no plan they were cut from")

    planned: dict[str, dict] = {}
    for path in plans:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                unit = json.loads(line)
                planned[str((unit.get("selected_on") or {}).get("candidate"))] = unit
    unplanned = sorted(key for key in drawn if key not in planned)
    assert not unplanned, (
        f"{len(unplanned)} of {len(drawn)} graded rows were cut from a plan that is no longer "
        f"on this machine: {unplanned[:5]}"
    )
    disagreeing = sorted(
        key
        for key, row in drawn.items()
        if bool(row["leveled"]) != bool(planned[key].get("leveled"))
    )
    assert not disagreeing, (
        f"{len(disagreeing)} graded rows disagree with their plan about whether the picture "
        f"went through a levelled colormap: {disagreeing[:5]}"
    )


def test_a_grade_is_keyed_the_way_the_retention_join_spells_a_ledger_row() -> None:
    """The two sides of the protection are one function, asserted rather than
    intended. `retention.render_key_of` builds its key off a ledger row's stored
    recipe and `gallery_grade.render_key` off a graded row; both go through
    [`labeling.finished.render_key`], and a second spelling of either would make
    the protection read as running while it marked nothing.
    """
    rows = two_rows_one_pair()
    assert gallery_grade.render_key(grade_of(rows[0]["recipe"])) == retention.render_key_of(rows[0])
    # That the store's key IS the finished stores' is `test_gallery_grade.py`'s;
    # what is new here is that a *ledger* row spells the same one.
    assert retention.render_key_of(rows[0]) == finished.render_key(grade_of(rows[0]["recipe"]))
