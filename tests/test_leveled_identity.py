"""The identity the `.leveled/` argument stands on.

**No prune can delete a `<stem>.leveled/` that a surviving row still resolves
through**, and the argument is structural rather than a rank or a policy one.
`prune` builds its doomed list as the `picture` of each row whose key is not in
the kept set; `candidate_ledger.sweep._delete_colormap` derives
`<parent>/<stem>.leveled` from *that row's own* picture; and
`curation.pool_draw.leveled_dir` derives `<parent>/<stem>.leveled` from a
*surviving* row's own picture. So the prune can only take a live directory if a
dropped row and a surviving row name **one picture**. See
`curation/README.md`'s *A prune cannot take a surviving row's colormap, and the
reason is structural*.

That has been measured twice and nothing pinned it, which is what this file is
for. Two halves, and they fail on different things:

* **The derivations are one expression** — [`the_same_directory`] below asks
  both, behaviourally, over every picture shape the store holds and over the
  near-misses that would break a naive one. It is fast, it needs no ledger, and
  it fails the day the writer, the sweeper or the draw is edited alone.
* **No two rows name one picture** — a scan, so it is in the slow lane. It does
  not merely count collisions: it asserts the **shape classification is total**,
  because a leg that names its files a third way is caught at its first row that
  way and only at its first *collision* the other. A shape is one of two, and
  each is injective for its own reason:

  | shape | stem | why it cannot collide |
  | ----- | ---- | --------------------- |
  | recipe-key | the ledger key itself | the store holds one row per key |
  | run-index | an attempt index | unique inside one run directory |

**The counts are held by a ratchet and not by a floor**, since 2026-09-07. A
floor — `>=` the number somebody measured — reads *the store only grows*, and
this store deletes by design: [`candidate_ledger.sweep.prune`] drops rows every
time a leg merges, so the first purposeful loss made the floor red with no repair
available except repointing it, which asserts nothing. What replaced it is
[`candidate_ledger.ratchet`]: the count now, plus every deletion a transaction
wrote down since the high-water mark, must still reach that mark. Loss is allowed
exactly when something accounted for it. **Repointing the mark at today's reading
is the forbidden edit** and always was — the mark moves on growth, by the prune,
mechanically.

**The reading it was written against**, 2026-09-06, over the ledger the ckpt-112
mine left: **308,419 rows**, every one naming a picture, every picture under the
tree, **308,419 distinct `(directory, stem)` pairs and zero carried by more than
one row**. **294,893** are recipe-key named — `depth` 286,843, `mine` 4,476,
`remode` 2,938, `hunt` 636 — over 95 directories, and **13,526** are run-index
named — `runs` 11,402, `reframe_draw` 2,124 — over 11. **The two shapes share no
directory**, so they cannot collide with each other either.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fractal_wallpapers import paths
from fractal_wallpapers.curation import pool_draw
from fractal_wallpapers.curation.candidate_ledger import ratchet, sweep

#: What the reading above says, so a scan that disagrees says so against a number
#: somebody wrote down rather than against nothing.
READING = {
    "rows": 308_419,
    "recipe_key_named": 294_893,
    "run_index_named": 13_526,
    "key_named_directories": 95,
    "index_named_directories": 11,
}


# --------------------------------------------------------------------------- #
# The two derivations are one expression.
# --------------------------------------------------------------------------- #
def removed_by_the_prune(picture: Path) -> Path | None:
    """The directory `_delete_colormap` actually takes for one picture.

    Asked by running it, not by re-spelling it: a guard that restated the
    expression would agree with itself forever, which is the one thing it must
    not do."""
    before = {entry for entry in picture.parent.iterdir() if entry.is_dir()}
    sweep._delete_colormap(picture, {"colormaps": 0, "colormap_bytes": 0, "unreadable": 0}, print)
    gone = before - {entry for entry in picture.parent.iterdir() if entry.is_dir()}
    assert len(gone) <= 1, f"the prune took {len(gone)} directories for one picture: {gone}"
    return next(iter(gone), None)


#: The stems worth asking about: the two live shapes, and the near-misses a
#: derivation built on string surgery rather than on `stem` would get wrong.
STEMS = (
    # The recipe-key shape, which is what 294,893 rows carry.
    "1f0b3c8e9a2d4f6b8c0e2a4d6f8b0c2e4a6d8f0b2c4e6a8d0f2b4c6e8a0d2f4b",
    # The run-index shape, which is what 13,526 carry.
    "0042",
    "00017",
    # A stem holding the suffix itself, and one holding a dot.
    "0042.leveled",
    "0042.jpg",
    "a.b.c",
    # A stem that is another stem's prefix, so a `startswith` would take both.
    "0042x",
)


@pytest.mark.parametrize("stem", STEMS)
def test_the_prune_and_the_draw_derive_one_directory_from_one_picture(tmp_path, monkeypatch, stem):
    """`pool_draw.leveled_dir` names exactly what `_delete_colormap` removes.

    This is the whole structural half of the argument. If they ever spell the
    directory differently, the prune deletes one thing while the draw plans on
    another, and the failure is silent both ways: a plan naming a directory that
    is gone, or a directory nothing will ever clear."""
    root = tmp_path / "artifacts"
    directory = root / "curation" / "depth" / "leg" / "pictures"
    directory.mkdir(parents=True)
    picture = directory / f"{stem}.jpg"
    picture.write_bytes(b"")
    colormap = directory / f"{stem}.leveled"
    colormap.mkdir()
    (colormap / "map.json").write_text("{}", encoding="utf-8")
    # A decoy that only a wrong derivation reaches.
    decoy = directory / f"{stem}x.leveled"
    decoy.mkdir()

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    stored = paths.tracked_name(picture)

    drawn = pool_draw.leveled_dir(stored)
    assert drawn is not None, f"the draw found no colormap beside {stored}"
    assert Path(drawn) == colormap

    taken = removed_by_the_prune(picture)
    assert taken == colormap
    assert Path(drawn) == taken
    assert decoy.is_dir(), "the prune reached a directory that is not this picture's"


def test_the_draw_says_nothing_where_the_operator_did_not_act(tmp_path, monkeypatch):
    """No directory is not a gap; it is the common case, and both sides agree."""
    root = tmp_path / "artifacts"
    directory = root / "curation" / "runs" / "leg" / "pictures"
    directory.mkdir(parents=True)
    picture = directory / "0042.jpg"
    picture.write_bytes(b"")

    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    assert pool_draw.leveled_dir(paths.tracked_name(picture)) is None
    assert removed_by_the_prune(picture) is None
    assert pool_draw.leveled_dir(None) is None
    assert pool_draw.leveled_dir("data/palettes/inferno.json") is None


# --------------------------------------------------------------------------- #
# The naming shapes, and the scan that fails when a third one lands.
# --------------------------------------------------------------------------- #
def shapes_of(rows, tiers=None) -> dict:
    """`{how the pictures are named, and what collides}` over any row list.

    A row is `(key, stored picture)`. The classification is the guard: a stem
    that is neither the row's own key nor unique inside its directory is a
    **third naming shape**, and a third shape is the only way a prune could ever
    reach a live colormap. It is reported whether or not it has collided yet."""
    resolved = paths.Tiers.current() if tiers is None else tiers
    out = {
        "rows": 0,
        "no_picture": [],
        "outside_the_tree": [],
        "recipe_key_named": 0,
        "run_index_named": 0,
        "key_directories": set(),
        "index_directories": set(),
        "shared_by_two_rows": [],
    }
    seen: dict[tuple[str, str], str] = {}
    for key, picture in rows:
        out["rows"] += 1
        if not picture:
            out["no_picture"].append(key)
            continue
        where = paths.rehome(picture, resolved)
        if where is None:
            out["outside_the_tree"].append(key)
            continue
        pair = (str(where.parent), where.stem)
        first = seen.setdefault(pair, key)
        if first != key:
            out["shared_by_two_rows"].append((first, key, pair))
        # Through the shipped classifier and not a second spelling of it: a prune
        # records what it took under these same two names, and a census counting
        # by one expression against a recording made by another is two readings
        # that drift without either one ever looking wrong.
        if ratchet.shape_of(picture, key) == ratchet.RECIPE_KEY:
            out["recipe_key_named"] += 1
            out["key_directories"].add(pair[0])
        else:
            out["run_index_named"] += 1
            out["index_directories"].add(pair[0])
    out["distinct_pairs"] = len(seen)
    out["directories_in_both_shapes"] = sorted(out["key_directories"] & out["index_directories"])
    return out


def test_the_scan_names_a_third_shape_and_the_collision_it_would_bring():
    """The scan below is only worth running if it bites, so this is it biting.

    Two rows sharing a stem inside one directory is the collision, and a shape
    that puts a key-named row and an index-named row in one directory is the
    thing that *permits* it — reported even before it has happened, which is the
    whole reason this is a classification and not a duplicate count."""
    tree = f"{paths.ARTIFACTS_NAME}/curation"

    clean = shapes_of(
        [
            ("aaaa", f"{tree}/depth/leg/pictures/aaaa.jpg"),
            ("bbbb", f"{tree}/depth/leg/pictures/bbbb.jpg"),
            ("runs|0001", f"{tree}/runs/leg/pictures/0001.jpg"),
            ("runs|0002", f"{tree}/runs/leg/pictures/0002.jpg"),
        ]
    )
    assert clean["shared_by_two_rows"] == []
    assert clean["directories_in_both_shapes"] == []
    assert (clean["recipe_key_named"], clean["run_index_named"]) == (2, 2)

    collided = shapes_of(
        [
            ("aaaa", f"{tree}/depth/leg/pictures/shared.jpg"),
            ("bbbb", f"{tree}/depth/leg/pictures/shared.jpg"),
        ]
    )
    assert len(collided["shared_by_two_rows"]) == 1
    assert collided["distinct_pairs"] == 1

    mixed = shapes_of(
        [
            ("cccc", f"{tree}/hunt/leg/pictures/cccc.jpg"),
            ("hunt|00007", f"{tree}/hunt/leg/pictures/00007.jpg"),
        ]
    )
    assert mixed["shared_by_two_rows"] == []
    assert mixed["directories_in_both_shapes"], (
        "a directory holding both shapes is where an index can grow into a key and "
        "the scan has to say so before it does"
    )


def test_the_ratchets_first_mark_is_the_census_this_file_records(tracked_ratchet_log):
    """The mark the scan is held to is the reading in this file's docstring.

    Arithmetic over a tracked file, so it costs nothing and runs in the fast lane
    — and it is what stops the mark being a number with no provenance. The seed
    row was written once, by hand, out of [`READING`]; every row after it is a
    prune's. If those two ever disagree the guard is measuring against something
    nobody wrote down, which is the state the floor it replaced ended in."""
    seeded = [row for row in ratchet.entries(tracked_ratchet_log) if row["event"] == ratchet.MARK]
    assert seeded, f"{tracked_ratchet_log} holds no mark, so the scan below bounds nothing"
    first = seeded[0]
    assert first["schema"] == ratchet.LOG_SCHEMA
    assert first["counts"] == {name: READING[name] for name in ratchet.COUNTERS}


@pytest.mark.slow
def test_no_two_ledger_rows_name_one_picture(tracked_ledger, tracked_ratchet_log):
    """The measured half, over every row there is. The rows are the session's one
    reading; see `conftest.tracked_ledger`.

    `tiers` is handed in, which is the difference between six seconds and nine
    minutes over this store — see [`fractal_wallpapers.paths.rehome`]. The counts
    are asserted against [`READING`] loosely, as *no shape this reading never
    saw*: an exact equality would fail on the next merge, which is a census and
    not a defect, while a row classified into neither shape is the defect."""
    tiers = paths.Tiers.current()
    found = shapes_of(
        [(str(row.get("key")), row.get("picture")) for row in tracked_ledger.rows], tiers
    )

    assert found["no_picture"] == [], (
        f"{len(found['no_picture'])} row(s) name no picture, so nothing says which colormap "
        f"is theirs: e.g. {found['no_picture'][:3]}"
    )
    assert found["outside_the_tree"] == [], (
        f"{len(found['outside_the_tree'])} row(s) name a picture with no artifacts component, "
        f"which `rehome` cannot address: e.g. {found['outside_the_tree'][:3]}"
    )
    assert found["shared_by_two_rows"] == [], (
        f"{len(found['shared_by_two_rows'])} picture(s) are named by more than one ledger row, "
        f"so a prune that drops one of them takes the other's levelled colormap: "
        f"e.g. {found['shared_by_two_rows'][:3]}"
    )
    assert found["distinct_pairs"] == found["rows"]
    assert found["directories_in_both_shapes"] == [], (
        "a directory holds both a recipe-key named picture and a run-index named one. "
        "Neither shape can collide with itself; together in one directory they can, the "
        "day an index reaches a name a key already has: "
        f"{found['directories_in_both_shapes'][:3]}"
    )
    # The census against the ratchet, which is the half that used to be a floor.
    standing = ratchet.reading(tracked_ratchet_log)
    assert set(standing["mark"]) >= set(ratchet.COUNTERS), (
        f"the ratchet has never marked {sorted(set(ratchet.COUNTERS) - set(standing['mark']))}, "
        f"so nothing bounds those counters from below. {tracked_ratchet_log} is seeded by hand "
        f"once and advanced by every prune after that."
    )
    for counter in ratchet.COUNTERS:
        mark, forgiven = standing["mark"][counter], standing["deleted"][counter]
        assert found[counter] + forgiven >= mark, (
            f"{counter} reads {found[counter]:,} against a high-water mark of {mark:,} taken "
            f"{standing['marked_at'][counter]}, and only {forgiven:,} of the "
            f"{mark - found[counter]:,} missing are accounted for. A prune records what it "
            f"takes, so an unaccounted "
            f"shortfall of {mark - found[counter] - forgiven:,} is rows that left this store "
            f"without any transaction saying so. Read {tracked_ratchet_log}; do NOT repoint "
            f"the mark at today's count, which is what makes this guard worthless."
        )
