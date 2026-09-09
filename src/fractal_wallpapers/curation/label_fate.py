"""What became of every wallpaper a person graded 4, one rung at a time.

Three stores hold a human 4: `data/smooth_render/` and `data/strange_render/`,
the two finished-render corpora, and `data/gallery_grade/`, the fine head's own
thousand-row sitting. Since `label-migration merge` those verdicts are all
**ledger rows by key**, and that is what makes this exact rather than inferred —
a graded picture and a candidate the solve walked past are one object, so *what
happened to it* has an answer per row instead of a distribution.

## The rungs

A picture stops at the first of five that holds it:

```
0  OFF THE ROSTER        not in the seatable pool at all — a mode `mode_policy`
                         weights 0, a rejection somebody recorded, no picture on
                         disk. No bar ever read it.
1  BELOW THE COARSE BAR  never reaches the fine head: `gallery-grade score-pool`
                         runs on coarse-clears only, so a row under the render
                         judge's own bar cannot be seated at any fine bar.
2  BELOW THE FINE BAR    cleared coarse, read under [`solve.DEFAULT_FINE_BAR`],
                         and so outside the view before a rule ran.
3  REFUSED               cleared both and took no seat. The rule named is the
                         FIRST one that refused it, in [`rules.RULES`] order, and
                         not the only one — a row the location rule took would
                         very often also have met the cell allowance.
4  SEATED                it is in the record.
```

**Rung 0 is not a quibble.** Calling an off-roster row *below the coarse bar*
would say a bar refused a picture no bar ever read, and 6% of this population is
in modes the roster weights 0.

Rungs 0 to 2 are arithmetic over the ledger and the two score columns. Rungs 3
and 4 come from the solve itself, through [`solve.explained`], which is why
[`fates`] needs a record taken with `--explain-keys` naming this population and
refuses one that was not. A rung read off the aggregate refusal columns instead
would be a guess, and the point of this leg is that it does not have to guess.

## ★ The picture beside it is the point, and it is not always the same picture

A rung on its own says a wallpaper lost; the pair says what it lost **to**, and
whether that is a trade anybody would make. Which picture that is depends on the
rung, and getting it wrong is how a page lies quietly:

- **A refused card shows the row that beat it at the rule that refused it**, off
  [`PAIRING`]. For a `cell_allowance` refusal that is a picture somewhere else
  entirely — the marginal seat in the full cell — and **not** whatever sits at
  its own location, which is what this page showed until 2026-09-08 and which
  was simply the wrong picture for 348 of its 524 cards.
- **Every other rung shows the seat holding its place**, matched on the exact
  location, which for them is the right comparison.

Where there is nothing to show the card says which silence it is: a place the
record does not hold, or a refusal with no nameable competitor at all. Both are
more interesting answers than a gap.

**The gap is on every paired card** — both `p_fine` readings and the difference.
A refusal losing by 0.01 and one losing by 0.4 are different findings and a page
that named only the winner would flatten them into one.

Both sides are rendered fresh at [`sheets.LABEL_RESOLUTION`], which is also
[`release.RELEASE_REGIME`] — the geometry a person judged at and the geometry a
wallpaper ships at are one — so a fresh pair is a fair comparison where the
stored 640x360 candidate beside a 1280x720 judged render would not be. The
render inherits its levelling through [`stamps.for_release`] rather than
re-deciding it at the larger size, and it passes `mode_params`. Both of those
are rulings this project paid for.

## The three things the page has to say about itself

Each makes a column mean less than it looks:

- **`p_fine` where production has none.** A rung-0 or rung-1 row has no pool
  reading at all, because nothing ever asked the fine head about it. Where a
  `label_migration` store is named, its staged reading is shown instead and
  marked as **the migration's** rather than the pool's.
- **Both score columns are contaminated, and not equally.** Seven in ten of the
  finished-store rows are the render judge's own training data, so `p_ge4` is
  partly recognition there. **Every gallery-grade row is in the fine head's own
  corpus**, so for that third of the population `p_fine` is recognition too.
  There is no one honest column over the whole page and the legend says which is
  which where.
- **A row whose `mode_params` was non-empty used not to be the picture its key
  names, and the page flagged it.** `mine.make` dropped the settings until
  2026-09-08, so the pool held 10,664 rows drawn bare under a varied key: the
  fresh render here was correct and the *scores* beside it had been read off the
  bare picture. What was flagged was decided on the **maker**, which the picture's
  own path records. All 10,664 were re-rendered and re-scored the same day —
  see [`REPAIRED_STORE_WIDE`] — so nothing is flagged now, and a card still says
  which settings a row carries, that being a fact worth having either way.

## The verbs

```
keys         the three stores -> one key manifest, for `solve --explain-keys`
population   the stores joined to the ledger, with rungs 0 to 2 decided
fates        a record's `explained` block -> rungs 3 and 4, and the seat per place
competitors  the row that beat each refused one, off the rebuilt seating state
render       every graded picture, every seat, every competitor, at label geometry
page         an index and one page per rung slice, p_fine ascending
```

`keys` runs before the solve and the rest after it. Each writes one file and
reads the ones before it, so a killed stage costs itself and nothing earlier —
and `render` reads the pictures already on disk, so re-running it after
`competitors` draws only what the new pairings added.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.labeling import finished, gallery_grade
from fractal_wallpapers.labeling.sheets import LABEL_RESOLUTION, LABEL_SUPERSAMPLE

#: The schema every row and record this module writes carries.
SCHEMA = 1

#: Where a store lands unless a caller names one. Under the ignored scratch tree
#: for [`label_migration.DEFAULT_STORE`]'s reason: what this leg makes is a
#: reading, and nothing in the pipeline may find a reading by accident.
DEFAULT_STORE = Path("scratch") / "label_fate"

#: The files one store holds, in the order the verbs write them.
KEYS_NAME = "keys.txt"
POPULATION_NAME = "population.jsonl"
FATES_NAME = "fates.json"
COMPETITORS_NAME = "competitors.json"
RENDERS_NAME = "renders.jsonl"
PAGE_NAME = "index.html"

#: Where the fresh label-geometry renders go, and where the page's reduced copies
#: go. Two directories because they are two things: the first is the leg's output
#: at shipping size and is worth keeping, the second is a display artifact of one
#: page and is rebuilt with it.
PICTURES_NAME = "pictures"
PAGE_PICTURES = "page_pictures"

#: The human verdict this leg is about. **4**, the top of both scales — and the
#: only class where "the pipeline disagreed with a person" is worth a picture.
GRADE = 4

#: How wide each picture on the page is written, and at what quality. **Both
#: sides at one width**, which is the whole claim the page makes.
PAGE_WIDTH = 640
PAGE_QUALITY = 88

#: How many engines the render verb drives. **Three**, this machine's render
#: pool, and a rule about the desktop rather than a knob.
WORKERS = 3

#: The kill deadline stamped onto every render task, in seconds. A label-geometry
#: render is four times a candidate's pixels, so this is [`solve.ROW_BACKSTOP`]'s
#: purpose at this leg's size: no row is declined, but no row hangs the leg.
ROW_BACKSTOP = 900.0

#: How much of this population each head was **fitted on**, measured rather than
#: assumed and carried here rather than recomputed per page.
#:
#: `JUDGE_TRAIN` is how many of the finished-render label-4 rows are in the
#: shipped render judge's own train side, reconstructed at its recorded
#: `source_commit` in `MERGE_ckpt116_label_rows_and_resolve_0908` and cross-checked
#: against that split's `train_tiers["4"]`. **It is not `sides_for(0)`'s reading
#: today** — the corpora have grown 577 rows since the judge shipped, and today's
#: `train_tiers["4"]` is 1,357 over a corpus this judge was never fitted on. A page
#: quoting the live figure would overstate the contamination.
#:
#: `FINE_TRAIN`/`FINE_STOPPING` are the gallery-grade grade-4 rows by side, off
#: `artifacts/gallery_grade_head/split.json`. They sum to **every** gallery-grade
#: row on the page, which is the point: that store *is* the fine head's corpus.
#: The `store.POOL_SUBTREES` whose maker has always passed `mode_params`, so a
#: picture under one of them is what its recipe key says. `hunt.Maker.make` takes
#: them off the plan and `label_migration` renders through `colorize.render`
#: naming them; every other subtree went through `mine.make`, or has not been
#: checked, and is flagged. **Adding a name here is a claim somebody measured.**
SETTINGS_AWARE_SUBTREES = ("hunt", "label_migration")

JUDGE_TRAIN = 1271
FINE_TRAIN = 245
FINE_STOPPING = 67

#: The rungs, in the order a picture meets them, with what each says on the page.
#: A row stops at the first that holds it, and the page counts them.
RUNGS: tuple[tuple[str, str], ...] = (
    (
        "off_the_roster",
        "not in the seatable pool at all: a mode the roster weights 0, a rejection "
        "somebody recorded, a picture the sweep took. No bar ever read it",
    ),
    (
        "below_the_coarse_bar",
        "never reaches the fine head. `gallery-grade score-pool` runs on coarse-clears "
        "only, so a row under the render judge's bar cannot be seated at any fine bar",
    ),
    (
        "below_the_fine_bar",
        "cleared the coarse bar and read under the fine bar, so it was outside the view "
        "before any seating rule ran",
    ),
    (
        "refused",
        "cleared both bars and took no seat. The rule named is the FIRST that refused "
        "it and not the only one",
    ),
    ("seated", "it holds a seat in the record"),
)

#: The rung names, spelled once so a caller never types one.
OFF_THE_ROSTER, BELOW_COARSE, BELOW_FINE, REFUSED, SEATED = (name for name, _ in RUNGS)


class FateRefused(RuntimeError):
    """A store, a record or a column this leg cannot run without."""


# --------------------------------------------------------------------------- #
# the store.
# --------------------------------------------------------------------------- #
def store_root(store: str | Path | None = None) -> Path:
    """Where one reading of this question lives."""
    return Path(DEFAULT_STORE if store is None else store)


def _path(store, name: str) -> Path:
    return store_root(store) / name


def pictures_dir(store: str | Path | None = None) -> Path:
    """Where the fresh label-geometry renders land."""
    return store_root(store) / PICTURES_NAME


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FateRefused(f"{path} is not there. Run the verb that writes it first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# the population, and the keys that name it.
# --------------------------------------------------------------------------- #
def graded(log=print) -> tuple[dict, dict]:
    """`({ledger key: entry}, per-store verdict counts)` for every wallpaper graded 4.

    The join is different on each side and neither half is a guess. A
    finished-render row carries the whole recipe of the picture somebody judged,
    at label geometry, so its ledger key is [`label_migration.recipe_of`]'s
    derivation of it at candidate geometry — the same call `label-migration
    derive` makes, so the two agree by construction and not by coincidence. A
    gallery-grade row was *drawn from* the pool and carries
    `selected_on.candidate`, which already **is** a ledger key.

    **`labeler` is not read.** Every gallery-grade row carries `matt` and every
    finished-render row carries `null`, so a filter on it would drop two stores of
    one person's verdicts to keep the third.

    A key graded in more than one store is **one** entry carrying every verdict.
    29 are, which is one wallpaper judged twice and never two wallpapers.
    """
    from fractal_wallpapers.curation import colorize, label_migration
    from fractal_wallpapers.curation import recipes as recipes_module
    from fractal_wallpapers.palettes import groups as groups_module

    band = colorize.band()
    groups = groups_module.member_groups()
    held: dict = {}
    counts: dict = {}
    for head in finished.HEADS:
        resolution = finished.resolved(head)
        for row in resolution.scored():
            if int(row["score"]) != GRADE:
                continue
            recipe = label_migration.recipe_of(row, band, groups)
            key = str(recipes_module.key_of(recipe))
            entry = held.setdefault(key, {"key": key, "verdicts": []})
            entry["verdicts"].append(
                {
                    "store": head,
                    "grade": GRADE,
                    "batch": row.get("batch"),
                    "recorded_at": row.get("recorded_at"),
                    "labeler": row.get("labeler"),
                    "judged_picture": label_migration.label_picture(head, row),
                }
            )
            counts[head] = counts.get(head, 0) + 1
    for row in gallery_grade.resolved().current.values():
        if int(row.get("grade") or 0) != GRADE:
            continue
        key = str(((row.get("selected_on") or {}).get("candidate")) or "")
        if not key:
            continue
        entry = held.setdefault(key, {"key": key, "verdicts": []})
        entry["verdicts"].append(
            {
                "store": gallery_grade.NAME,
                "grade": GRADE,
                "batch": row.get("batch"),
                "recorded_at": row.get("recorded_at"),
                "labeler": row.get("labeler"),
                # A gallery-grade sitting judges the CANDIDATE's own picture at
                # label geometry off a sheet this leg does not keep, so there is
                # no stored judged file to name. The fresh render is the picture.
                "judged_picture": None,
            }
        )
        counts[gallery_grade.NAME] = counts.get(gallery_grade.NAME, 0) + 1
    log(
        f"[graded] {len(held):,} wallpaper(s) graded {GRADE} over "
        f"{sum(counts.values()):,} verdict(s) — {counts}"
    )
    return held, counts


def keys(store=None, log=print) -> dict:
    """The population's ledger keys, one per line. Writes [`KEYS_NAME`].

    Written **before** the solve, because it is the solve's `--explain-keys`
    argument: the fate of a row that took no seat exists only inside the pass that
    refused it, and a record not asked about these keys cannot be asked afterwards.
    """
    began = time.time()
    held, counts = graded(log)
    where = _path(store, KEYS_NAME)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text("".join(f"{key}\n" for key in sorted(held)), encoding="utf-8", newline="\n")
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "grade": GRADE,
        "keys": len(held),
        "verdicts": sum(counts.values()),
        "by_store": counts,
        "path": str(where),
        "seconds": round(time.time() - began, 1),
    }
    log(f"[keys] {len(held):,} key(s) -> {where}")
    return record


def population(store=None, log=print) -> dict:
    """The graded rows joined to the ledger, rungs 0 to 2 decided. Writes [`POPULATION_NAME`].

    **This is the pool-holding half.** It streams the ledger for the population's
    own rows and reads the score sidecar whole, which is what any leg asking a
    question about the pool costs; it is why the rungs are decided here once and
    the render and the page never open the store again.

    Rungs 0 to 2 are decided against the same three conditions the solve applies,
    read off the same modules rather than restated:
    [`mode_policy.routed_mode_of`] and the four other pool exclusions for rung 0,
    [`solve.Q4_BAR`] for rung 1 — the height `gallery-grade score-pool` stops
    reading at — and [`solve.DEFAULT_FINE_BAR`] for rung 2.

    **The routed mode and not the recipe's.** A modulate whose texture moved
    nothing is a smooth picture on both questions, so asking the recipe would put
    rows on rung 0 that the pool holds perfectly well.
    """
    from fractal_wallpapers.curation import candidate_ledger, mode_policy, solve
    from fractal_wallpapers.models import gallery_grade_train

    began = time.time()
    held, counts = graded(log)
    rows = candidate_ledger.by_key(set(held))
    log(f"[population] {len(rows):,} of {len(held):,} key(s) are in the ledger")
    coarse = candidate_ledger.scores_by_recipe(candidate_ledger.read_scores())
    fine = gallery_grade_train.read_pool_scores()
    if not fine:
        raise FateRefused(
            f"{gallery_grade_train.pool_scores_path()} is not there, so no row has a "
            "p_fine and every rung below the coarse bar would read as one. Run "
            "`fractal-wallpapers gallery-grade score-pool` first."
        )
    present = candidate_ledger.present_pictures(list(rows.values()))

    out: list[dict] = []
    for key in sorted(held):
        entry = held[key]
        row = rows.get(key)
        read = coarse.get(key) or {}
        seen = fine.get(key) or {}
        recipe = (row or {}).get("recipe") or {}
        routed = None if row is None else mode_policy.routed_mode_of(row)
        off = _off_the_roster(row, routed, present, read, mode_policy)
        p_ge4 = None if not read else float(read["p_ge4"])
        p_fine = None if not seen else float(seen["p_ge4"])
        if off is not None:
            rung, why = OFF_THE_ROSTER, off
        elif p_ge4 is None or p_ge4 < solve.Q4_BAR:
            rung, why = BELOW_COARSE, f"p_ge4 under {solve.Q4_BAR:g}"
        elif p_fine is None or p_fine < solve.DEFAULT_FINE_BAR:
            rung, why = BELOW_FINE, f"p_fine under {solve.DEFAULT_FINE_BAR:g}"
        else:
            # Rungs 3 and 4 are the solve's to say. Left unset rather than
            # guessed: `fates` fills them from a record's `explained` block, and a
            # row still carrying this when the page is built is a row the record
            # was never asked about.
            rung, why = None, None
        out.append(
            {
                "schema": SCHEMA,
                "key": key,
                "verdicts": entry["verdicts"],
                "stores": sorted({verdict["store"] for verdict in entry["verdicts"]}),
                "in_the_ledger": row is not None,
                "mode": str(recipe.get("mode") or ""),
                "routed_mode": routed,
                "mode_params": dict(recipe.get("mode_params") or {}),
                "colormap": str(recipe.get("colormap") or ""),
                "palette_group": str(recipe.get("palette_group") or ""),
                "location": None if row is None else str((row.get("location") or {}).get("key")),
                "partition": None if row is None else str(row.get("partition")),
                "picture": None if row is None else row.get("picture"),
                "p_ge4": p_ge4,
                "p_ge3": None if not read else float(read["p_ge3"]),
                "p_fine": p_fine,
                "p_fine_from": None if p_fine is None else "pool",
                "rung": rung,
                "why": why,
            }
        )
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "grade": GRADE,
        "wallpapers": len(out),
        "verdicts": sum(counts.values()),
        "by_store": counts,
        "in_the_ledger": sum(1 for row in out if row["in_the_ledger"]),
        "bars": {
            "coarse": {"column": "p_ge4", "at": float(solve.Q4_BAR), "from": "solve.Q4_BAR"},
            "fine": {
                "column": "p_fine(>=4)",
                "at": float(solve.DEFAULT_FINE_BAR),
                "from": "solve.DEFAULT_FINE_BAR",
            },
        },
        "rungs": _counted(out),
        "undecided": sum(1 for row in out if row["rung"] is None),
        "with_mode_params": sum(1 for row in out if row["mode_params"]),
        "path": str(_write_jsonl(_path(store, POPULATION_NAME), out)),
        "seconds": round(time.time() - began, 1),
    }
    log(f"[population] {len(out):,} wallpaper(s); {record['rungs']}")
    return record


def _off_the_roster(row, routed, present, read, mode_policy) -> str | None:
    """Why [`solve.pool`] would refuse this row, or `None` where it would not.

    The five exclusions in that function's own order, each a fact about the
    candidate rather than a quality bar — so a row here never reached a bar and
    saying it was *below* one would be false.
    """
    if row is None:
        return "no ledger row"
    if not mode_policy.is_accepted(routed):
        return f"mode {routed} is off the roster"
    if row.get("rejected"):
        return "somebody rejected it"
    if not row.get("at_candidate_regime"):
        return "not at candidate regime"
    if not row.get("picture"):
        return "the row names no picture"
    if str(row["key"]) not in present:
        return "its picture is not on disk"
    if not read:
        return "no reading on the live judge"
    return None


def _counted(rows) -> dict:
    """`{rung: how many}` in [`RUNGS`] order, with the undecided left out."""
    out = {name: 0 for name, _ in RUNGS}
    for row in rows:
        if row.get("rung"):
            out[row["rung"]] += 1
    return out


# --------------------------------------------------------------------------- #
# the fates the solve alone knows.
# --------------------------------------------------------------------------- #
def fates(stamp: str, store=None, log=print) -> dict:
    """Rungs 3 and 4, and the seat at each row's place. Writes [`FATES_NAME`].

    Reads the solve record behind one tentative stamp. **It refuses a record with
    no `explained` block, and one whose block does not name every row here**: a
    rung read off the aggregate refusal columns instead would be a guess about
    which of several rules acted first, and the whole point of doing this after
    `label-migration merge` is that it no longer has to be a guess.

    The seat is matched on the exact location. A place the record does not hold
    gets `None` and the card says so; `another_place_is_the_same_place` is called
    out separately, because there the place did not merely lose — it was folded
    into a neighbour at pool construction, and the record does not carry which
    neighbour.
    """
    from fractal_wallpapers.curation import candidate_ledger, solve, tentative
    from fractal_wallpapers.models import gallery_grade_train

    began = time.time()
    rows = _read_jsonl(_path(store, POPULATION_NAME))
    if not rows:
        raise FateRefused("no population.jsonl in this store. Run `population` first.")
    manifest = tentative.read_manifest(stamp)
    # `solve.name` and not the path: a record and its stamped folder share a name
    # by construction (`_record_a_solve`), and `read_record` takes the name.
    named = (manifest.get("solve") or {}).get("name")
    if not named:
        raise FateRefused(
            f"{stamp}'s manifest names no solve record, so the pass that chose those "
            "seats cannot be read and nothing can say why a row took no seat."
        )
    record = solve.read_record(str(named))
    explained = (record.get("rejection") or {}).get("explained") or {}
    if not explained:
        raise FateRefused(
            f"the solve behind {stamp} carries no `rejection.explained` block, so the "
            "fate of a row that took no seat is not recorded anywhere and cannot be "
            "recovered after the fact. Re-run `curate solve record --explain-keys "
            f"{_path(store, KEYS_NAME)}`."
        )
    wanted = {row["key"] for row in rows}
    missing = sorted(wanted - set(explained))
    if missing:
        raise FateRefused(
            f"{len(missing):,} of {len(wanted):,} key(s) here are not in {stamp}'s "
            f"`explained` block — {missing[:3]}. That record was asked about a different "
            "population, and a rung this leg filled in from it would be about that one."
        )

    seats = {str(seat["location"]): seat for seat in tentative.read_rows(stamp)}
    fine = gallery_grade_train.read_pool_scores()
    seat_rows = candidate_ledger.by_key({str(seat["key"]) for seat in seats.values()})
    filled = 0
    for row in rows:
        verdict = str(explained[row["key"]])
        if row["rung"] is None:
            row["rung"] = SEATED if verdict == solve.SEATED else REFUSED
            row["why"] = None if verdict == solve.SEATED else verdict
            filled += 1
        # The refusal is recorded on EVERY row and not only the ones it decided,
        # because a row that never reached the view still has one — the solve says
        # `below_its_mode_bar` — and a reader comparing the two columns is
        # entitled to see that this leg's rung and the solve's word agree.
        row["explained"] = verdict
        seat = seats.get(row["location"] or "")
        row["seat"] = None if seat is None else _seat_of(seat, seat_rows, fine)
    out = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "stamp": stamp,
        "record": (manifest.get("solve") or {}).get("record"),
        "explained": len(explained),
        "filled": filled,
        "rungs": _counted(rows),
        "places_held": sum(1 for row in rows if row.get("seat")),
        "places_empty": sum(1 for row in rows if not row.get("seat")),
        "same_place": sum(1 for row in rows if row["explained"] == solve.SAME_PLACE),
        "path": str(_write_jsonl(_path(store, POPULATION_NAME), rows)),
        "seconds": round(time.time() - began, 1),
    }
    _write_json(_path(store, FATES_NAME), out)
    log(f"[fates] {filled:,} rung(s) filled from {stamp}; {out['rungs']}")
    return out


def _seat_of(seat: dict, seat_rows: dict, fine: dict) -> dict:
    """One seat as the card shows it: mode, palette, `p_fine`, and its recipe.

    The palette is off the **ledger row** and not the seat, because a gallery row
    carries the mode and the key and has never carried the colormap — and a
    caption naming the map is what makes the pair readable as a trade.
    """
    key = str(seat["key"])
    recipe = (seat_rows.get(key) or {}).get("recipe") or {}
    read = fine.get(key) or {}
    return {
        "key": key,
        "alias": seat.get("alias"),
        "seat": seat.get("seat"),
        "mode": str(seat.get("mode") or recipe.get("mode") or ""),
        "mode_params": dict(seat.get("mode_params") or recipe.get("mode_params") or {}),
        "colormap": str(recipe.get("colormap") or ""),
        "p_ge4": None if seat.get("p_ge4") is None else float(seat["p_ge4"]),
        "p_fine": None if not read else float(read["p_ge4"]),
        "picture": seat.get("picture"),
        "recipe": recipe or None,
    }


# --------------------------------------------------------------------------- #
# the competitor: the row whose removal would admit a refused one.
# --------------------------------------------------------------------------- #
#: What a refused card is paired with, and where each pairing comes from.
#:
#: **The definition is [`rules.State.counted_requirements`]' own set for the rule
#: that refused, and is not restated here.** That method returns one set of seated
#: keys per rule the candidate fails — the seats that rule would accept a
#: departure from — so the rows that beat it *at the rule that took it* is a thing
#: the seating rules define rather than a thing a page decides. Where the set
#: holds more than one seat, the **marginal** member is the weakest by the pass's
#: own seating key, which is the seat a 1-swap ejects first; ties break on the
#: key, so the answer never depends on dict order.
#:
#: ⚠ **It is deliberately NOT [`rules.State.removals`]**, which is the
#: intersection across *every* rule the candidate fails and answers a stricter
#: question: which single seat leaving would be **enough**. Those are different
#: and the difference is large — 101 of the 102 location refusals here fail the
#: cell allowance as well, so their intersection is empty and `removals` names
#: nothing at all, while the seat standing at their place is plainly the row that
#: beat them. The intersection is reported per card as `enough` rather than used
#: as the pairing, because *what beat me* and *what would be enough* are both
#: worth knowing and only the first is a picture.
PAIRING = {
    "location": "the seat standing at its own place — that one seat is the whole of the "
    "location rule's requirement, so there is nothing to choose between",
    "cell_allowance": "the marginal seat in the cell that refused it: the weakest, by this "
    "pass's own seating key, of the seats already dominant in that cell",
    "twin": "the seated picture the diversity rule measured it against, off the record's own "
    "`diversity_refusals` — a single-member requirement per neighbour",
    "another_place_is_the_same_place": "NOTHING. The place was folded into a neighbour at "
    "pool construction, before any seat existed, and the record does not carry which "
    "neighbour absorbed it — so there is no seat to name and the card says so",
}


def competitors(stamp: str, store=None, log=print) -> dict:
    """The row whose removal would admit each refused one. Rewrites the population.

    **Pool-holding, and it rebuilds the pass's final state rather than guessing at
    it.** The seated candidates come from [`solve.pool`] — the same objects the
    solve walked, so the cells, families, group and mode behind every count are
    the pass's own and not a re-derivation — and they are seated into a
    [`rules.State`] carrying the record's own ceiling, spiral cap and mode
    ceilings. Seating is order-independent for every counted rule, so the
    finished state is the pass's finished state.

    **It proves the rebuild before it uses it.** `counted_refusal` is asked of
    every refused row and must return exactly what the record's `explained` block
    says, for all of them; a single disagreement refuses the whole verb rather
    than pairing 523 cards correctly and one card with a picture that never
    competed with anything.
    """
    from fractal_wallpapers.curation import ceiling, rules, solve, tentative

    began = time.time()
    rows = _read_jsonl(_path(store, POPULATION_NAME))
    if not rows:
        raise FateRefused("no population.jsonl in this store. Run `population` first.")
    manifest = tentative.read_manifest(stamp)
    record = solve.read_record(str((manifest.get("solve") or {}).get("name")))
    config = record["config"]
    seats = [str(seat["key"]) for seat in tentative.read_rows(stamp)]

    candidates, _refused = solve.pool(log=log)
    held = {str(candidate.key): candidate for candidate in candidates}
    state = rules.State(
        ceiling.Rule(
            targets=config["ceiling"].get("targets") or {},
            group_cap=int(config["ceiling"]["group_cap"]),
            k=config["ceiling"]["k"],
        ),
        int(config["n"]),
        diversity=None,
        spiral_cap=config.get("spiral_cap"),
        mode_ceilings=config.get("mode_ceilings") or {},
    )
    for key in seats:
        state.seat(held[key], "recorded")
    log(f"[competitors] {state.filled:,} seat(s) rebuilt into the pass's final state")

    # The proof, over the refusals `counted_refusal` is the one that DECIDES.
    #
    # Two are decided somewhere else and are excluded by name rather than by
    # silence, because a state rebuilt from the seats cannot be asked about
    # either: `twin` is the diversity rule's, kept per key in the record's own
    # `diversity_refusals`; and `another_place_is_the_same_place` is taken at
    # POOL CONSTRUCTION, before a seat exists — so asking the counted rules about
    # one of those 71 rows gets an answer about a rule that never ran on it. The
    # first run of this verb reported exactly that, 71 rows deep, which is the
    # guard doing its job rather than a disagreement to paper over.
    decided_elsewhere = ("twin", solve.SAME_PLACE)
    order = solve.ranking_for(candidates, config["sort_key_named"], log=lambda *_: None)[0]
    twins = record.get("diversity_refusals") or {}
    wrong = []
    for row in rows:
        if row["rung"] != REFUSED or row["explained"] in decided_elsewhere:
            continue
        candidate = held.get(row["key"])
        said = None if candidate is None else state.counted_refusal(candidate)
        if said != row["explained"]:
            wrong.append({"key": row["key"], "record": row["explained"], "rebuild": said})
    if wrong:
        raise FateRefused(
            f"the rebuilt state disagrees with {stamp}'s own `explained` block on "
            f"{len(wrong):,} row(s) — {wrong[:3]}. Every pairing below is read off that "
            "state, so a disagreement makes all of them suspect rather than most of them "
            "right."
        )
    asked = sum(
        1 for row in rows if row["rung"] == REFUSED and row["explained"] not in decided_elsewhere
    )
    log(f"[competitors] the rebuild reproduces all {asked:,} counted refusal(s) exactly")

    counts: dict = {}
    for row in rows:
        row["competitor"] = None
        if row["rung"] != REFUSED:
            continue
        why = row["explained"]
        counts[why] = counts.get(why, 0) + 1
        if why == "twin":
            against = (twins.get(row["key"]) or {}).get("too_close_to")
            row["competitor"] = _competitor(against, held, order, why)
        elif why in ("location", "cell_allowance"):
            candidate = held[row["key"]]
            row["competitor"] = _marginal(_refusing_set(state, candidate, why), held, order, why)
            # The stricter question, kept beside the pairing rather than instead
            # of it: whether ONE seat leaving would have been enough.
            if row["competitor"] is not None:
                row["competitor"]["enough"] = sorted(state.counted_removals(candidate))[:1]
        # `another_place_is_the_same_place` keeps `None` on purpose. See PAIRING.
    paired = [row for row in rows if row.get("competitor")]
    distinct = {row["competitor"]["key"] for row in paired}
    _dress(paired, distinct)
    out = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "stamp": stamp,
        "pairing": PAIRING,
        "refused": sum(counts.values()),
        "by_rule": dict(sorted(counts.items(), key=lambda item: -item[1])),
        "paired": len(paired),
        "unpairable": sum(
            1 for row in rows if row["rung"] == REFUSED and not row.get("competitor")
        ),
        "distinct_competitors": len(distinct),
        "already_rendered": len(distinct & _on_disk(store)),
        "one_removal_would_be_enough": sum(
            1 for row in paired if (row["competitor"] or {}).get("enough")
        ),
        "one_removal_is_never_enough_is": "the candidate fails a second rule as well, so "
        "`removals` — the intersection across every failing rule — is empty. It still lost "
        "to the row named on the card; no single departure would have admitted it",
        "path": str(_write_jsonl(_path(store, POPULATION_NAME), rows)),
        "seconds": round(time.time() - began, 1),
    }
    _write_json(_path(store, COMPETITORS_NAME), out)
    log(f"[competitors] {len(paired):,} paired over {len(distinct):,} distinct row(s)")
    return out


def _dress(paired: list, distinct: set) -> None:
    """Give every competitor the palette and `p_fine` its caption needs.

    One keyed ledger read and one pool-scores read for the whole page, because a
    competitor is a *seat* and 453 cards share 116 of them — a lookup per card
    would read the same rows four times over.

    **The gap goes on the card**, both readings and the difference: a refusal
    losing by 0.01 and one losing by 0.4 are different findings, and a page that
    showed only which one won would flatten them into the same picture.
    """
    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.models import gallery_grade_train

    seats = candidate_ledger.by_key(distinct)
    fine = gallery_grade_train.read_pool_scores()
    for row in paired:
        rival = row["competitor"]
        recipe = (seats.get(rival["key"]) or {}).get("recipe") or {}
        read = fine.get(rival["key"]) or {}
        rival["colormap"] = str(recipe.get("colormap") or "")
        rival["mode_params"] = dict(recipe.get("mode_params") or {})
        rival["p_fine"] = None if not read else float(read["p_ge4"])
        mine = row.get("p_fine")
        rival["gap"] = (
            None if rival["p_fine"] is None or mine is None else round(rival["p_fine"] - mine, 6)
        )


def _refusing_set(state, candidate, why: str) -> set:
    """The seats the rule that refused this candidate would accept a departure from.

    Mirrors [`rules.State.counted_refusal`]'s own loop so the set belongs to the
    rule that actually acted and not to some later one the candidate also fails:
    the cell taken is the **first** over-full cell in the candidate's own order,
    which is the cell `counted_refusal` returned on.
    """
    if why == "location":
        held = state.places.get(candidate.location)
        return set() if held is None else {held}
    for cell in candidate.cells:
        if len(state.cells.get(cell, ())) + 1 > state.rule.allowed(cell, state.n):
            return set(state.cells.get(cell, ()))
    return set()


def _on_disk(store) -> set:
    """Every key this store already has a label-geometry picture for."""
    return {path.stem for path in pictures_dir(store).glob("*.jpg")}


def _marginal(could: set, held: dict, order, why: str) -> dict | None:
    """The weakest of the seats the refusing rule would take a departure from.

    Weakest by the pass's own seating key, because that is the seat a 1-swap
    ejects first — so it is the row that would actually step aside rather than
    any row that could. `solve.value_of` reads the key the record was seated on,
    so this does not care which key that was.
    """
    from fractal_wallpapers.curation import solve

    if not could:
        return None
    ranked = sorted(could, key=lambda key: (solve.value_of(held[key], order), str(key)))
    return _competitor(ranked[0], held, order, why, alternatives=len(could))


def _competitor(key, held: dict, order, why: str, alternatives: int = 1) -> dict | None:
    """One competitor, as the card shows it."""
    from fractal_wallpapers.curation import solve

    candidate = held.get(str(key or ""))
    if candidate is None:
        return None
    return {
        "key": str(candidate.key),
        "why": why,
        "how": PAIRING[why],
        "alternatives": int(alternatives),
        "value": float(solve.value_of(candidate, order)),
        "mode": str(candidate.mode),
        "location": str(candidate.location),
    }


# --------------------------------------------------------------------------- #
# the renders. Both sides, one geometry.
# --------------------------------------------------------------------------- #
def render(store=None, workers: int = WORKERS, log=print) -> dict:
    """Every graded picture and every seat beside one, at label geometry.

    One pass over both sides, because they are the same render: a graded row and
    the seat that took its place are both ledger rows, and drawing them through
    two paths would put the difference between the paths into the comparison the
    page exists to make.

    **What each render is told is the row's whole recipe.** `mode_params`,
    because `mine.make` dropped them and the pool is full of varied keys drawn
    bare; `curve` and `palette`, because a third of this population came out of
    the label corpora and carries knobs the candidate path never spends — a plain
    render of one of those is a picture of something else under its name. The
    levelling is **inherited** off the candidate's own stamp
    ([`stamps.for_release`]) rather than re-measured at the larger size.

    Resumable on the file: [`release.run_pass`] is given only the rows whose
    picture is not already there, so a killed leg costs the rows it was holding.
    """
    from fractal_wallpapers.curation import backfill, release
    from fractal_wallpapers.curation import recipes as recipes_module
    from fractal_wallpapers.curation import stamps as stamps_module

    began = time.time()
    rows = _read_jsonl(_path(store, POPULATION_NAME))
    if not rows:
        raise FateRefused("no population.jsonl in this store. Run `population` first.")
    regime = release.RELEASE_REGIME
    if tuple(regime.resolution) != tuple(LABEL_RESOLUTION) or regime.supersample != int(
        LABEL_SUPERSAMPLE
    ):
        raise FateRefused(
            f"this leg draws both sides at the geometry a person judged at, "
            f"{list(LABEL_RESOLUTION)}ss{LABEL_SUPERSAMPLE}, and reaches it through "
            f"release.RELEASE_REGIME, which now reads {regime.spelled}. The two have moved "
            "apart, so name the geometry here or put the constant back."
        )
    wanted = _wanted(rows)
    log(f"[render] {len(wanted):,} picture(s) wanted at {regime.spelled}")

    from fractal_wallpapers.curation import candidate_ledger

    ledger = candidate_ledger.by_key(set(wanted))
    borrowed = stamps_module.for_release(
        ledger, backfill.read(), regime=recipes_module.CANDIDATE_REGIME.spelled, store="sequence"
    )
    log(f"[render] {len(borrowed):,}/{len(ledger):,} row(s) inherit a levelling curve")

    where = pictures_dir(store)
    where.mkdir(parents=True, exist_ok=True)
    tasks, already = [], []
    for key in sorted(wanted):
        row = ledger.get(key)
        picture = where / f"{key}.jpg"
        if picture.is_file() and release.decodable(picture):
            already.append(key)
            continue
        if row is None:
            continue
        recipe = row["recipe"]
        tasks.append(
            release.task_for(
                id=key,
                row=recipe,
                mode=recipe["mode"],
                colormap=recipe["colormap"],
                mode_params=recipe.get("mode_params"),
                curve=recipe.get("curve"),
                palette=recipe.get("palette"),
                autolevel=borrowed.get(key),
                output=picture,
                geometry={**regime.geometry(), "maxiter": int(recipe["maxiter"])},
                timeout=ROW_BACKSTOP,
            )
        )
    log(f"[render] {len(tasks):,} to draw, {len(already):,} already on disk")

    made: dict = {}
    failed: list = []
    written = _path(store, RENDERS_NAME)

    def sink(task, result):
        if result.ok:
            made[task.id] = str(result.info["picture"])
        else:
            failed.append({"key": task.id, "why": result.error})
            log(f"[render] {task.id} failed: {result.error}")

    leg = release.run_pass(tasks, int(workers), sink, log, leg=None)
    held = [
        {
            "schema": SCHEMA,
            "key": key,
            "picture": made.get(key) or str(where / f"{key}.jpg"),
            "made": key in made or key in already,
            "reused": key in already,
            "side": wanted[key],
        }
        for key in sorted(wanted)
        if key in made or key in already
    ]
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "regime": regime.spelled,
        "geometry": regime.geometry(),
        "workers": int(workers),
        "row_backstop_seconds": ROW_BACKSTOP,
        "inherited_a_curve": len(borrowed),
        "wanted": len(wanted),
        "graded": sum(1 for side in wanted.values() if "graded" in side),
        "seats": sum(1 for side in wanted.values() if "seat" in side),
        "competitors": sum(1 for side in wanted.values() if "competitor" in side),
        "already": len(already),
        "made": len(made),
        "failed": failed,
        "not_in_the_ledger": sorted(key for key in wanted if key not in ledger),
        "killed": leg.get("killed", 0),
        "not_started": len(leg.get("not_started", [])),
        "path": str(_write_jsonl(written, held)),
        "seconds": round(time.time() - began, 1),
    }
    log(f"[render] {len(made):,} made, {len(already):,} reused, {len(failed):,} failed")
    return record


def _wanted(rows) -> dict:
    """`{key: which side of the page it is on}` over both sides of every card.

    A key can be more than one — a graded wallpaper that took the seat at its own
    place, a seat that is also somebody else's marginal competitor — and is drawn
    once, which is the point of keying the render on the recipe and not on the
    card. Many refusals share a marginal row, so this is where that collapses.
    """
    out: dict = {}
    for row in rows:
        if row.get("in_the_ledger"):
            out.setdefault(row["key"], []).append("graded")
        seat = row.get("seat")
        if seat and seat.get("key"):
            out.setdefault(str(seat["key"]), []).append("seat")
        rival = row.get("competitor")
        if rival and rival.get("key"):
            out.setdefault(str(rival["key"]), []).append("competitor")
    return {key: sorted(set(sides)) for key, sides in out.items()}


# --------------------------------------------------------------------------- #
# the page.
# --------------------------------------------------------------------------- #
#: How many cards one page carries. **150**, chosen by loading them rather than
#: by taste: the single 2,107-card page this replaced is 2.1 MB of markup over
#: 4,214 lazy images and the browser stalls scrolling it, where 150 cards is
#: ~150 KB and paints at once. The split follows the sort and never reorders, so
#: page 1 of a rung is always that rung's largest disagreements.
PAGE_SIZE = 150

#: The rung that is **counted and not shown**, Matt's call of 2026-09-08. Those
#: rows are in modes `mode_policy` weights 0: no bar ever read them and no rule
#: ever refused them, so there is no comparison to draw and a section of them
#: would say there was. The index carries the count, so the rungs still add to
#: the population.
NOT_SHOWN = (OFF_THE_ROSTER,)

STYLE = """
 body { font: 13px/1.45 system-ui, sans-serif; margin: 1.5rem;
        background: #14161a; color: #dfe3e8; }
 a { color: #7fa6d8; }
 h1 { font-size: 1.2rem; margin: 0 0 .4rem; }
 h2 { font-size: 1rem; margin: 1.8rem 0 .3rem; }
 .lede, .rung-note { max-width: 66rem; color: #9aa4b1; margin: 0 0 1rem; }
 .lede b, .rung-note b { color: #dfe3e8; }
 .lede em { color: #d8b45a; font-style: normal; }
 .legend { max-width: 66rem; margin: 0 0 1.5rem; padding: .7rem .9rem;
           background: #1c1f26; border-radius: 6px; color: #9aa4b1; }
 .legend li { margin: .3rem 0; }
 .legend b { color: #dfe3e8; }
 .legend .warn { color: #d8b45a; }
 .nav { margin: 0 0 1.2rem; padding: .5rem .7rem; background: #1c1f26;
        border-radius: 6px; display: flex; gap: 1.2rem; flex-wrap: wrap;
        max-width: 84rem; }
 .nav .here { color: #dfe3e8; font-weight: 600; }
 .idx { max-width: 72rem; border-collapse: collapse; }
 .idx td { padding: .25rem .9rem .25rem 0; vertical-align: top; }
 .idx .n { color: #d8b45a; text-align: right; }
 .idx .pages a { margin-right: .35rem; }
 .row { background: #1c1f26; border-radius: 6px; margin: 0 0 1rem; overflow: hidden;
        max-width: 84rem; }
 .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; background: #0e1013; }
 figure { margin: 0; position: relative; }
 img { display: block; width: 100%; }
 figcaption { position: absolute; left: 0; top: 0; background: rgba(10,12,15,.78);
              padding: .15rem .45rem; font-size: .68rem; letter-spacing: .04em;
              text-transform: uppercase; color: #9aa4b1; }
 .judged figcaption { color: #d8b45a; }
 .facts { display: flex; flex-wrap: wrap; gap: .15rem 1.1rem; padding: .5rem .7rem; }
 .facts.seat { padding-top: 0; color: #8f98a4; }
 .facts span { white-space: nowrap; }
 .lab { color: #6b7480; }
 .gap { color: #e07b53; font-weight: 600; }
 .key { font-family: ui-monospace, monospace; color: #6b7480; font-size: .72rem; }
 .flag { color: #e07b53; }
 .staged { color: #7fa6d8; }
 .gone { padding: 4rem 1rem; text-align: center; color: #6b7480; }
 .empty { padding: 3.5rem 1rem; text-align: center; color: #8f98a4;
          background: #191c22; }
"""

PAGE = """<!doctype html>
<meta charset="utf-8"><title>{title}</title>
<style>{style}</style>
<h1>{heading}</h1>
{nav}
{body}
"""


def page(store=None, migration_store=None, repaired_seats_of=None, log=print) -> dict:
    """One card per wallpaper, in rung order, `p_fine` ascending inside each rung.

    Ascending because the head's largest disagreements with a person come first:
    a picture somebody called a 4 and the pipeline scored near zero is the row
    worth looking at, and a page sorted the other way buries every one of them.

    `migration_store` names a `label_migration` store whose staged scores stand in
    where production has none. A rung-0 or rung-1 row was never read by the fine
    head — that is what the rung *means* — so the column would otherwise be blank
    exactly where the disagreement is largest. It is marked as the migration's
    reading on every card that uses one and never mixed into the pool's column.
    """
    from PIL import Image

    began = time.time()
    rows = _read_jsonl(_path(store, POPULATION_NAME))
    if not rows:
        raise FateRefused("no population.jsonl in this store. Run `population` first.")
    read = _read_json(_path(store, FATES_NAME))
    # The PICTURE and not `renders.jsonl`. That file is the leg's record of what it
    # drew and is written once at the end, so a page keyed on it would show nothing
    # at all after a killed render — while every picture the leg finished is sitting
    # on disk. It is the same reasoning that makes the picture the resume token.
    drawn = pictures_dir(store)

    def made(key):
        where = drawn / f"{key}.jpg"
        return str(where) if where.is_file() else None

    staged = _staged_scores(migration_store)
    repaired = _repaired(repaired_seats_of)

    beside = store_root(store) / PAGE_PICTURES
    beside.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if row.get("p_fine") is None and row["key"] in staged:
            row["p_fine"] = float(staged[row["key"]])
            row["p_fine_from"] = "migration"

    counts = _counted(rows)
    legend = _legend(rows, counts, staged, repaired)
    slices = _slices(rows)
    missing = {"graded": 0, "against": 0}
    for one in slices:
        cards = []
        for row in one["rows"]:
            left = _beside(made(row["key"]), beside, f"{row['key']}.graded.jpg", Image)
            against, caption = _against(row)
            right = (
                None
                if not against
                else _beside(made(against), beside, f"{against}.against.jpg", Image)
            )
            missing["graded"] += left is None
            missing["against"] += bool(against) and right is None
            cards.append(_card(row, left, right, repaired, caption))
        _write_page(
            store,
            one["file"],
            title=f"{one['heading']} — page {one['page']} of {one['pages']}",
            heading=one["heading"],
            nav=_nav(one, slices),
            body=f'<p class="rung-note">{one["note"]}.</p>'
            + (f'<div class="legend"><ul>{legend}</ul></div>' if one["page"] == 1 else "")
            + "\n".join(cards),
        )
    index = _write_page(
        store,
        PAGE_NAME,
        title=f"what became of every wallpaper graded {GRADE}",
        heading=f"What became of every wallpaper graded {GRADE}",
        nav="",
        body=f'<p class="lede">{_lede(rows, read)}</p>'
        f'<div class="legend"><ul>{legend}</ul></div>{_index(rows, counts, slices)}',
    )
    record = {
        "schema": SCHEMA,
        "taken_at": _now(),
        "index": str(index),
        "pictures": str(beside),
        "pages": len(slices),
        "page_size": PAGE_SIZE,
        "entries": len(rows),
        "shown": sum(len(one["rows"]) for one in slices if not one["by_rule"]),
        "not_shown": {name: counts.get(name, 0) for name in NOT_SHOWN},
        "rungs": counts,
        "sorted_by": "p_fine ascending inside each rung; the split follows the sort",
        "width": PAGE_WIDTH,
        "staged_p_fine_used": sum(1 for row in rows if row.get("p_fine_from") == "migration"),
        "missing_pictures": missing,
        "seconds": round(time.time() - began, 1),
    }
    log(f"[page] {len(slices)} page(s) + index -> {index}")
    return record


def _write_page(store, name: str, *, title, heading, nav, body) -> Path:
    where = _path(store, name)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(
        PAGE.format(title=title, style=STYLE, heading=heading, nav=nav, body=body),
        encoding="utf-8",
        newline="\n",
    )
    return where


def slug(text: str) -> str:
    """A rung or rule name as a URL somebody can guess and type."""
    return str(text).replace("_", "-").strip("-")


def _slices(rows) -> list:
    """Every page this build writes: the rungs, then the refused rung again by rule.

    A rung is sorted and *then* cut, so the cut never reorders and page 1 is
    always the end of the sort a reader came for. The refused rung is written
    twice because its four rules are four different questions — a row the location
    rule took lost to the seat at its place, and a row the cell allowance took
    lost to a picture somewhere else entirely.
    """
    out: list = []
    for name, note in RUNGS:
        if name in NOT_SHOWN:
            continue
        out += _cut(
            _sorted(rows, lambda row, n=name: row.get("rung") == n),
            slug(name),
            _title(name),
            note,
            by_rule=False,
        )
    refused = [row for row in rows if row.get("rung") == REFUSED]
    for why in sorted({str(row["explained"]) for row in refused}):
        out += _cut(
            _sorted(refused, lambda row, w=why: str(row["explained"]) == w),
            f"{slug(REFUSED)}-{slug(why)}",
            f"REFUSED · {why}",
            f"each card is paired with {PAIRING.get(why, 'nothing')}",
            by_rule=True,
        )
    return out


def _sorted(rows, keep) -> list:
    mine = [row for row in rows if keep(row)]
    mine.sort(key=lambda row: (row.get("p_fine") is None, row.get("p_fine") or 0.0, row["key"]))
    return mine


def _cut(mine: list, stem: str, heading: str, note: str, by_rule: bool) -> list:
    pages = max(1, -(-len(mine) // PAGE_SIZE))
    return [
        {
            "file": f"{stem}-{at + 1:02d}.html",
            "stem": stem,
            "heading": heading,
            "note": note,
            "page": at + 1,
            "pages": pages,
            "by_rule": by_rule,
            "rows": mine[at * PAGE_SIZE : (at + 1) * PAGE_SIZE],
        }
        for at in range(pages)
    ]


def _nav(one: dict, slices: list) -> str:
    """The index, prev, next, and where in the rung this page is."""
    mine = [held for held in slices if held["stem"] == one["stem"]]
    at = one["page"] - 1
    parts = [f'<a href="{PAGE_NAME}">index</a>']
    if at > 0:
        parts.append(f'<a href="{mine[at - 1]["file"]}">&larr; prev</a>')
    parts.append(f'<span class="here">page {one["page"]} of {one["pages"]}</span>')
    if at + 1 < len(mine):
        parts.append(f'<a href="{mine[at + 1]["file"]}">next &rarr;</a>')
    parts.append(f'<span class="lab">{len(one["rows"]):,} cards, p_fine ascending</span>')
    return f'<div class="nav">{"".join(parts)}</div>'


def _index(rows, counts: dict, slices: list) -> str:
    """The rung table, the same refused rung split by rule, and the dropped line."""
    held = [
        _index_row(_title(name), counts.get(name, 0), _of(slices, slug(name), False), note)
        for name, note in RUNGS
        if name not in NOT_SHOWN
    ]
    out = f'<h2>By rung</h2><table class="idx">{"".join(held)}</table>'
    by_rule = []
    for why in sorted({str(row["explained"]) for row in rows if row.get("rung") == REFUSED}):
        mine = _of(slices, f"{slug(REFUSED)}-{slug(why)}", True)
        by_rule.append(
            _index_row(
                why,
                sum(len(one["rows"]) for one in mine),
                mine,
                PAIRING.get(why, "nothing — the card says why"),
            )
        )
    out += (
        "<h2>The refused rung again, split by the rule that refused</h2>"
        f'<p class="rung-note">The same <b>{counts.get(REFUSED, 0):,}</b> cards. Four '
        "different questions: what a row lost to depends entirely on which rule took it.</p>"
        f'<table class="idx">{"".join(by_rule)}</table>'
    )
    dropped = ", ".join(f"<b>{counts.get(name, 0):,}</b> {_title(name)}" for name in NOT_SHOWN)
    return out + (
        f'<h2>Counted and not shown</h2><p class="rung-note">{dropped} — rows in modes '
        "<code>mode_policy</code> weights 0. No bar ever read them and no rule ever refused "
        "them, so there is no comparison to draw; the count is here so the rungs still add "
        f"to the <b>{len(rows):,}</b> wallpapers.</p>"
    )


def _of(slices: list, stem: str, by_rule: bool) -> list:
    return [one for one in slices if one["stem"] == stem and one["by_rule"] is by_rule]


def _index_row(name: str, total: int, mine: list, note: str) -> str:
    links = " ".join(f'<a href="{one["file"]}">{one["page"]}</a>' for one in mine)
    return (
        f'<tr><td><b>{name}</b></td><td class="n">{total:,}</td>'
        f'<td class="pages">{links}</td><td>{note}</td></tr>'
    )


def _against(row: dict) -> tuple:
    """`(key of the picture beside this card, what its caption says)`.

    Two different pairings and the rung decides which: a refused card shows **the
    row that beat it at the rule that refused it**, which for a cell allowance is
    not the seat at its place and never was; every other rung shows the seat
    holding its place, which for them is the right comparison.
    """
    if row.get("rung") == REFUSED:
        rival = row.get("competitor")
        if rival is None:
            return None, None
        return str(rival["key"]), f"beat it · {rival['why']}"
    seat = row.get("seat") or {}
    if not seat.get("key"):
        return None, None
    return str(seat["key"]), f"seat {seat.get('seat')} · holds this place"


def _title(name: str) -> str:
    return name.replace("_", " ").upper()


def _staged_scores(migration_store) -> dict:
    """`{key: staged p_fine}` off a `label_migration` store, or `{}` for none named."""
    if migration_store is None:
        return {}
    from fractal_wallpapers.curation import label_migration

    where = label_migration.store_root(migration_store) / label_migration.SCORES_NAME
    return {
        str(row["key"]): float(row["fine"]["p_ge4"])
        for row in _read_jsonl(where)
        if (row.get("fine") or {}).get("p_ge4") is not None
    }


def _repaired(stamp) -> set:
    """The varied seats of a record the repair leg re-rendered by name, or `{}`.

    Named as a **stamp** rather than as a key list, because that is how the repair
    was scoped: `FIX_ckpt116_mine_mode_params_0908` took every seat of one record
    carrying a non-empty `mode_params` — twelve of them — and re-rendered each
    through the fixed path. So the record's own varied seats *are* the repaired
    set, and it stays right if the leg is run again against another record.

    Nothing outside those twelve was repaired, and the 10,652 varied rows still in
    the pool are the reason this page flags rather than assumes.
    """
    if not stamp:
        return set()
    from fractal_wallpapers.curation import tentative

    return {str(seat["key"]) for seat in tentative.read_rows(stamp) if seat.get("mode_params")}


def leg_of(picture) -> str:
    """`<subtree>/<leg>` off a stored picture's path, or `""` for one with no home.

    The picture path is where a row records **which maker drew it**, and after
    `mine.make` spent six days dropping `mode_params` that is the only durable
    place that fact lives. `store.POOL_SUBTREES` fixes the shape.
    """
    parts = str(picture or "").replace("\\", "/").split("/")
    try:
        at = parts.index("curation")
    except ValueError:
        return ""
    return "/".join(parts[at + 1 : at + 3]) if len(parts) > at + 2 else ""


#: When every varied row in the pool was re-rendered through the fixed path, and
#: how the population was derived. `PRECLOSEOUT_ckpt116_renderer_holes_and_repair_0908`
#: took `candidate_ledger.bare_varied` — the store's own answer to *which rows carry
#: settings their picture was not drawn with* — and re-rendered and re-scored all
#: **10,664** of them, 0 failed, every one reproducing its own recipe key.
#:
#: **So the flagged set below is empty, and that is why it is a constant rather
#: than a deletion.** The maker rule is still the right rule and is still the one
#: written down; what changed is that no row in the pool fails it any more. Set this
#: to `None` to switch the flag back on, which is what a leg found regressing would
#: want — a flag that stayed on over a repaired store would tell a reader to
#: distrust scores that are now correct, which is the same failure in the mirror.
REPAIRED_STORE_WIDE = "2026-09-08"


def drawn_bare(row: dict, repaired: set) -> bool:
    """Whether this row's stored picture is the **bare** mode under a varied key.

    Three ways it is not, and the first two are facts about the maker rather than
    about the row: `hunt.Maker.make` has always passed the settings, and
    `label_migration` renders through `colorize.render` naming them, so a picture
    under either subtree is what its key says whatever its settings are. The third
    is a row the repair leg re-rendered by name.

    Everything else with a non-empty `mode_params` would be flagged, including the
    subtrees nobody has checked. That is the safe direction: a picture that IS its
    key marked as suspect costs a reader one look, and a bare picture shown
    unmarked under a varied name is the failure this whole class of bug is.

    **[`REPAIRED_STORE_WIDE`] short-circuits all of it**, because the store-wide
    repair made the answer *no* for every row rather than for a named few. See that
    constant for why it is a switch and not a deletion.
    """
    if not row.get("mode_params"):
        return False
    if REPAIRED_STORE_WIDE is not None:
        return False
    if str(row["key"]) in repaired:
        return False
    return leg_of(row.get("picture")).split("/")[0] not in SETTINGS_AWARE_SUBTREES


def _beside(source, directory: Path, name: str, Image) -> str | None:
    """One picture copied beside the page at [`PAGE_WIDTH`]. Returns its relative name."""
    if not source:
        return None
    where = Path(source)
    if not where.is_file():
        return None
    out = directory / name
    if not out.is_file():
        with Image.open(where) as opened:
            image = opened.convert("RGB")
            if image.width != PAGE_WIDTH:
                height = max(1, round(image.height * PAGE_WIDTH / image.width))
                image = image.resize((PAGE_WIDTH, height), Image.LANCZOS)
            image.save(out, "JPEG", quality=PAGE_QUALITY)
    return f"{PAGE_PICTURES}/{name}"


def _score(value, marked: bool = False) -> str:
    if value is None:
        return '<span class="lab">—</span>'
    return f'<span class="staged">{float(value):.4f}*</span>' if marked else f"{float(value):.4f}"


def _mode(mode: str, params: dict) -> str:
    if not params:
        return str(mode)
    return f"{mode}@" + ",".join(f"{name}={value}" for name, value in sorted(params.items()))


def _card(row: dict, left, right, repaired: set, caption=None) -> str:
    against = row.get("competitor") if row.get("rung") == REFUSED else (row.get("seat") or {})
    against = against or {}
    staged = row.get("p_fine_from") == "migration"
    verdicts = " · ".join(
        f"{verdict['store']} {verdict['grade']}" for verdict in row.get("verdicts") or ()
    )
    facts = [
        f'<span><span class="lab">human</span> <b>{GRADE}</b> ({verdicts})</span>',
        f'<span><span class="lab">p_ge4</span> {_score(row.get("p_ge4"))}</span>',
        f'<span><span class="lab">p_fine</span> {_score(row.get("p_fine"), staged)}</span>',
        f'<span><span class="lab">mode</span> {_mode(row["mode"], row["mode_params"])}</span>',
        f'<span><span class="lab">palette</span> {row["colormap"]}</span>',
        f'<span><span class="lab">place</span> <span class="key">{row["location"]}</span></span>',
        f'<span class="key">{row["key"]}</span>',
    ]
    if row.get("why"):
        facts.insert(1, f'<span><span class="lab">first refused by</span> {row["why"]}</span>')
    if drawn_bare(row, repaired):
        facts.append(
            '<span class="flag">⚠ drawn bare under a varied key — the scores above were '
            "read off the bare picture, this render is not</span>"
        )
    elif row["mode_params"]:
        facts.append('<span class="lab">varied key, repaired 2026-09-08</span>')

    graded = (
        f'<figure class="judged"><img loading="lazy" src="{left}">'
        f"<figcaption>graded {GRADE} · fresh at 1280&times;720 ss2</figcaption></figure>"
        if left
        else '<figure class="judged"><div class="gone">no picture</div></figure>'
    )
    if not against:
        held = f'<figure><div class="empty">{_nothing(row)}</div></figure>'
        beneath = ""
    else:
        held = (
            f'<figure><img loading="lazy" src="{right}">'
            f"<figcaption>{caption or 'holds this place'}</figcaption></figure>"
            if right
            else '<figure><div class="gone">no picture</div></figure>'
        )
        gap = against.get("gap")
        beside = [
            f'<span><span class="lab">against</span> '
            f"{_mode(against.get('mode', ''), against.get('mode_params') or {})}</span>",
            f'<span><span class="lab">palette</span> {against.get("colormap", "")}</span>',
            f'<span><span class="lab">p_fine</span> {_score(against.get("p_fine"))}</span>',
        ]
        if gap is not None:
            beside.append(
                # SIGNED, and the sign is the finding rather than a detail: the
                # marginal seat in a full cell is by definition the weakest seat
                # in it, so it is usually WORSE on p_fine than the row it refused
                # — 326 of 453 on this page. A `+` glued on the front would have
                # printed `+-0.1638` and buried that behind what reads as a typo.
                f'<span><span class="lab">gap</span> <span class="gap">{gap:+.4f}</span></span>'
            )
        if against.get("alternatives", 1) > 1:
            beside.append(
                f'<span class="lab">marginal of {against["alternatives"]} seats the rule '
                "would take a departure from</span>"
            )
        if row.get("rung") == REFUSED and not against.get("enough"):
            beside.append(
                '<span class="lab">no single seat leaving would have been enough — it '
                "fails a second rule too</span>"
            )
        beside.append(f'<span class="key">{against.get("key", "")}</span>')
        beneath = f'<div class="facts seat">{"".join(beside)}</div>'
    return (
        f'<div class="row"><div class="pair">{graded}{held}</div>'
        f'<div class="facts">{"".join(facts)}</div>{beneath}</div>'
    )


def _nothing(row: dict) -> str:
    """What the right-hand side says when there is no picture to put there.

    Two different silences and the card must not blur them: a place the record
    simply does not hold, and a refusal with no nameable competitor at all.
    """
    if row.get("rung") == REFUSED:
        return (
            "no row to name<br><small>the pre-selection folded this place into a "
            "neighbour before any seat existed, and the record does not carry which "
            "one</small>"
        )
    return "no seat at this place<br><small>the record holds nothing here</small>"


def _lede(rows, read: dict) -> str:
    stores: dict = {}
    for row in rows:
        for store in row.get("stores") or ():
            stores[store] = stores.get(store, 0) + 1
    spelled = ", ".join(f"<b>{count:,}</b> {name}" for name, count in sorted(stores.items()))
    return (
        f"<b>{len(rows):,}</b> wallpapers a person graded <b>{GRADE}</b> — {spelled} — every "
        "one of them a ledger row by key since <code>label-migration merge</code>, so what "
        "follows is each one's <em>exact</em> fate in "
        f"<b>{read.get('stamp')}</b> and not an inference from a distribution. "
        "Four rungs and the one before them; a picture stops at the first that holds it. "
        "<em>Each card shows the graded picture beside the seat that holds its place</em>, "
        "both drawn fresh at the geometry it was judged at and a wallpaper ships at. "
        "Sorted by <b>p_fine ascending</b> inside each rung, so the largest disagreements "
        "come first."
    )


def _legend(rows, counts: dict, staged: dict, repaired: set) -> str:
    flagged = [row for row in rows if drawn_bare(row, repaired)]
    borrowed = sum(1 for row in rows if row.get("p_fine_from") == "migration")
    # Counted by store MEMBERSHIP and not as a partition, because 29 wallpapers
    # were graded 4 in both and the two figures beside these counts were measured
    # over the memberships: `JUDGE_TRAIN` over every key a finished store grades 4,
    # `FINE_TRAIN`/`FINE_STOPPING` over every gallery-grade row. Splitting the
    # overlap into one bucket would put a numerator over the wrong denominator.
    gallery = sum(1 for row in rows if gallery_grade.NAME in (row.get("stores") or ()))
    judged = sum(1 for row in rows if set(row.get("stores") or ()) & set(finished.HEADS))
    lines = [f"<b>{_title(name)}</b> — {counts.get(name, 0):,}" for name, _ in RUNGS]
    lines.append(
        '<span class="warn">Both score columns are contaminated, and not by the same '
        "amount.</span> Of the <b>"
        f"{judged:,}</b> rows a finished store grades {GRADE}, <b>{JUDGE_TRAIN:,}</b> are "
        "inside the shipped render judge's own train side, so <b>p_ge4</b> is largely "
        "recognition for them. Of the <b>"
        f"{gallery:,}</b> gallery-grade rows, <b>every one</b> is inside the fine head's "
        f"1,000-row corpus — {FINE_TRAIN} fitted on and {FINE_STOPPING} in its stopping "
        "slice — so for those <b>p_fine</b> is recognition too."
    )
    lines.append(
        "<b>So there is no one honest column over this page.</b> <b>p_fine</b> is the "
        "honest one for the two finished-render stores, where the fine head saw 1.1% of "
        "the rows; on a gallery-grade card neither column is a verdict on an unseen "
        "picture, and the human grade beside them is the only independent thing on it."
    )
    if borrowed:
        lines.append(
            f'<span class="staged">p_fine marked *</span> is the <b>label-migration</b> '
            f"reading and not the pool's: <b>{borrowed:,}</b> rows here were never read by "
            "the fine head in production, because <code>score-pool</code> runs on "
            "coarse-clears only."
        )
    if flagged:
        lines.append(
            f'<span class="flag">⚠ {len(flagged):,} rows carry a non-empty '
            "<code>mode_params</code></span> and were drawn by a maker that dropped them. "
            "Their pool picture was drawn <b>bare</b> under a varied key, so every score on "
            "the card was read off a different picture from the one shown. They are marked "
            "and were not quietly redrawn."
        )
    return "".join(f"<li>{line}</li>" for line in lines)


__all__ = [
    "BELOW_COARSE",
    "COMPETITORS_NAME",
    "PAIRING",
    "BELOW_FINE",
    "DEFAULT_STORE",
    "FATES_NAME",
    "GRADE",
    "KEYS_NAME",
    "OFF_THE_ROSTER",
    "PAGE_NAME",
    "PAGE_PICTURES",
    "PAGE_QUALITY",
    "PAGE_WIDTH",
    "PICTURES_NAME",
    "POPULATION_NAME",
    "REFUSED",
    "RENDERS_NAME",
    "ROW_BACKSTOP",
    "RUNGS",
    "SCHEMA",
    "SEATED",
    "WORKERS",
    "PAGE",
    "PAGE_SIZE",
    "NOT_SHOWN",
    "STYLE",
    "SETTINGS_AWARE_SUBTREES",
    "FateRefused",
    "drawn_bare",
    "leg_of",
    "competitors",
    "fates",
    "graded",
    "keys",
    "page",
    "slug",
    "pictures_dir",
    "population",
    "render",
    "store_root",
]
