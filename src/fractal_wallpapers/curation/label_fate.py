"""What became of every **gallery-grade** wallpaper a person graded 4, one rung at a time.

Three stores hold a human 4: `data/smooth_render/` and `data/strange_render/`,
the two finished-render corpora, and `data/gallery_grade/`, the fine head's own
thousand-row sitting. Since `label-migration merge` those verdicts are all
**ledger rows by key**, and that is what makes this exact rather than inferred —
a graded picture and a candidate the solve walked past are one object, so *what
happened to it* has an answer per row instead of a distribution.

## One store, and it is [`STORE`]

This leg read all three until 2026-09-09 and put them on one page, which
conflated two populations that mean different things. A gallery-grade 4 is a
verdict on **a candidate this pool holds**, taken off a sheet drawn from the pool
itself; a finished-render 4 is a verdict on a picture from the finished corpora,
carried back to a ledger key through [`label_migration.recipe_of`]. Whether a
coarse-store 4 is a gallery-grade 4 **is not known** — nobody has graded those
rows on the gallery-grade scale — so putting them on a page about *fate* asks a
fate question of rows whose membership in the population is itself the open
question. **That is a different question and it does not have a page here.**

So the population is the gallery-grade store alone. Everything downstream reads
what [`population`] wrote, so the narrowing happens in [`graded`] and nowhere
else.

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
- **A row that lost its cluster's seat to a sibling place shows that sibling**,
  with the cluster it is seated under and each place's **neutral distance** to it.
  It is a `location` card like any other, because a pooled fold refuses nothing:
  the row stayed in the pool and lost a seat to a near-duplicate of its own place.
- **A folded place, on a record taken before 2026-09-09, shows the place that
  absorbed it**, off that record's own `preselection.refusals`, with the neutral
  distance the fold was taken at. Nothing beat those rows: the whole place went at
  pool construction, before a seat existed. The constant is read and never written.
- **Every other rung shows the seat holding its place**, matched on the exact
  location, which for them is the right comparison.

Where there is nothing to show the card says which silence it is: a place the
record does not hold, or a refusal with no nameable competitor at all. Both are
more interesting answers than a difference of two scores.

**Both `p_fine` readings and their difference are on every paired card**, under
the name `p_fine Δ` and beside the **leg that placed the competitor**. A refusal
whose competitor reads 0.01 above it and one whose competitor reads 0.4 above it
are different findings and a page naming only the winner would flatten them.

⚠ **That column was called `gap` until 2026-09-09 and the name was wrong** — see
[`P_FINE_DELTA_IS`]. It is not a measure of how close a row came to a seat and
there is no such quantity on this page: the rules that refuse compare no scores
at all. The leg is what explains a negative one, so it goes on the card first.

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
- **`p_fine` is recognition on this page, for every row on it.** The population
  *is* the fine head's own corpus — [`FINE_TRAIN`] fitted on and
  [`FINE_STOPPING`] in its stopping slice, summing to the whole of it — so the
  column that sorts the page is the head reading rows it was fitted to. The human
  grade beside it is the only independent thing on a card, and the page says that
  once and plainly rather than in a footnote. It is also why this is a page about
  **fate** and not about the head's accuracy: what a card shows is which rule
  stopped a wallpaper somebody wanted, and the column is there to order the
  disagreements, not to be believed.
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
keys         the gallery-grade store -> one key manifest, for `solve --explain-keys`
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

from fractal_wallpapers.labeling import gallery_grade
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

#: The one store this leg reads. **`gallery_grade` alone since 2026-09-09**, and
#: the reason is at the head of this module: a coarse-store 4 and a gallery-grade
#: 4 are verdicts on two different questions, and whether the first implies the
#: second is unanswered. A page carrying both answered a fate question about rows
#: whose membership was itself the open question.
#:
#: It is a constant and not a parameter on purpose. The old shape is one argument
#: away from being rebuilt, and rebuilding it is the thing that was stopped.
STORE = gallery_grade.NAME

#: The `store.POOL_SUBTREES` whose maker has always passed `mode_params`, so a
#: picture under one of them is what its recipe key says. `hunt.Maker.make` takes
#: them off the plan and `label_migration` renders through `colorize.render`
#: naming them; every other subtree went through `mine.make`, or has not been
#: checked, and is flagged. **Adding a name here is a claim somebody measured.**
SETTINGS_AWARE_SUBTREES = ("hunt", "label_migration")

#: How much of this population the fine head was **fitted on**, measured rather
#: than assumed and carried here rather than recomputed per page. The gallery-grade
#: grade-4 rows by side, off `artifacts/gallery_grade_head/split.json`. They sum to
#: **every** row on the page, which is the point and is the page's one caveat:
#: that store *is* the fine head's corpus, so `p_fine` here is recognition and
#: never a reading of an unseen picture.
#:
#: `JUDGE_TRAIN` sat beside these until 2026-09-09 and was 1,271 — how many
#: finished-render label-4 rows were inside the shipped render judge's own train
#: side. It went with the finished stores: no row on this page comes from one.
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

#: How far along a rung is, for the one question a *pair* of readings raises:
#: which way did a row move. [`RUNGS`] is already written in the order a picture
#: meets them, so the index into it is the answer and there is no second ordering
#: to keep in step — **forward** is a row getting further before something stopped
#: it, and `seated` is as far as forward goes.
RUNG_ORDER = {name: at for at, (name, _) in enumerate(RUNGS)}


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

    [`STORE`] and nothing else. A gallery-grade row was *drawn from* the pool and
    carries `selected_on.candidate`, which already **is** a ledger key, so there
    is no derivation here at all and nothing to get wrong.

    ⚠ **The two finished-render corpora were read here until 2026-09-09.** Their
    join was the other one: a finished row carries the whole recipe of the picture
    somebody judged, at label geometry, so its ledger key came from
    [`label_migration.recipe_of`] at candidate geometry — the same call
    `label-migration derive` makes. That was sound and is not why they went; they
    went because a page mixing the two answers a fate question about a population
    two different gradings define. See this module's own head.

    **`labeler` is not read.** Every gallery-grade row carries `matt`, so a filter
    on it says nothing this store does not already say.
    """
    held: dict = {}
    counts: dict = {}
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
    into a neighbour at pool construction, before any seat existed. **Which
    neighbour is on the record**, in the pre-selection's own `refusals` block, and
    [`competitors`] reads it off there.
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
    "location": "the one seat standing in this row's CLUSTER — that seat is the whole of "
    "the location rule's requirement, so there is nothing to choose between. Where it "
    "stands at a sibling place rather than at this row's own, the card also names the "
    "cluster and each place's neutral distance to the place the cluster is seated under",
    "cell_allowance": "the marginal seat in the cell that refused it: the weakest, by this "
    "pass's own seating key, of the seats already dominant in that cell",
    "twin": "the seated picture the diversity rule measured it against, off the record's own "
    "`diversity_refusals` — a single-member requirement per neighbour",
    "another_place_is_the_same_place": "the strongest candidate at the place that ABSORBED "
    "it, off the record's own `preselection.refusals` — a place and not a seat, folded at "
    "pool construction before any seat existed, so the card names the neutral distance the "
    "fold was taken at rather than a seating gap. **Retired 2026-09-09** and read only for "
    "records taken before it: a pooled fold destroys no row, so a row that loses its "
    "cluster's seat is refused by `location` above and has a sibling to name",
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

    ⚠ **The record's own fold is re-applied first, and a pooled record is wrong
    without it.** `solve.pool` hands back rows with no cluster on them, but
    [`rules.State.places`] is keyed on [`solve.Candidate.cluster`] — so a state
    rebuilt from the bare pool seats every row under its own location and a row
    that lost its **cluster's** seat to a sibling place looks like a row at a
    place nobody took. That is not a near miss: it moved 9 of this population's
    175 refusals off `location` on the first pooled record built here, some to
    `cell_allowance` and some to no refusal at all. The relabel is read off
    `preselection.folds`, which is the fold that pass actually took, and never
    re-derived — this pool is not the pool that pass ran over.

    **It proves the rebuild before it uses it.** `counted_refusal` is asked of
    every refused row and must return exactly what the record's `explained` block
    says, for all of them; a single disagreement refuses the whole verb rather
    than pairing 523 cards correctly and one card with a picture that never
    competed with anything. That guard is what found the missing fold: it reported
    those 9 rather than drawing them against pictures that never competed.
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
    # `{key: the demand or leg that placed it}`, off the record's own seats — the
    # fact that explains a negative `p_fine_delta` on a card. See `_competitor`.
    placed = {
        str(seat["key"]): str(seat.get("seated_for") or "") or None
        for seat in (record.get("seated") or ())
    }

    candidates, _refused = solve.pool(log=log)
    # `refusals` on a record whose fold DELETED and `folds` on one that pooled —
    # the same rows either way, and the second name exists precisely because
    # nothing was refused. See `distinct.POOL`.
    preselection = record.get("preselection") or {}
    absorbed = {
        str(entry["location"]): entry
        for entry in (preselection.get("refusals") or preselection.get("folds") or [])
    }
    candidates = _refolded(candidates, absorbed, preselection, log=log)
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
    # The fold is keyed by PLACE and names the picture that took it, so the
    # absorbing candidate is looked up on the picture rather than re-derived as
    # "the strongest row there now": this pool is not the pool that pass ran over,
    # and a re-derivation could name a row the pre-selection never saw.
    by_picture = {str(candidate.picture): candidate for candidate in candidates}
    wrong, vacated = [], []
    for row in rows:
        if row["rung"] != REFUSED or row["explained"] in decided_elsewhere:
            continue
        candidate = held.get(row["key"])
        said = None if candidate is None else state.counted_refusal(candidate)
        if said == row["explained"]:
            continue
        # ⚠ `None` is NOT a disagreement, and the distinction is the record's own.
        # `solve`'s refusal map is "the rule that refused it, THE LAST TIME IT WAS
        # OFFERED", and the search is anytime: a 1-swap or an augmenting chain can
        # eject the very seat that refused a row after it was last offered, and
        # then the final state refuses that row by nothing at all. The record is
        # right and so is the rebuild — they are answers about two moments. Such a
        # card has no competitor to name, which is what the pairing already does
        # with an empty requirement set, so it is counted and named rather than
        # papered over. A mismatch between two NAMED rules is still a real
        # disagreement and still refuses the verb.
        (vacated if said is None else wrong).append(
            {"key": row["key"], "record": row["explained"], "rebuild": said}
        )
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
    log(
        f"[competitors] the rebuild reproduces {asked - len(vacated):,} of {asked:,} counted "
        f"refusal(s) exactly; {len(vacated):,} were refused by a seat the pass later moved"
    )

    counts: dict = {}
    for row in rows:
        row["competitor"] = None
        if row["rung"] != REFUSED:
            continue
        why = row["explained"]
        counts[why] = counts.get(why, 0) + 1
        if why == "twin":
            against = (twins.get(row["key"]) or {}).get("too_close_to")
            row["competitor"] = _competitor(against, held, order, why, placed)
        elif why in ("location", "cell_allowance"):
            candidate = held[row["key"]]
            row["competitor"] = _marginal(
                _refusing_set(state, candidate, why), held, order, why, placed
            )
            # The stricter question, kept beside the pairing rather than instead
            # of it: whether ONE seat leaving would have been enough.
            if row["competitor"] is not None:
                row["competitor"]["enough"] = sorted(state.counted_removals(candidate))[:1]
                if why == "location":
                    _fold(row, held, absorbed, preselection)
        elif why == solve.SAME_PLACE:
            # The old constant, still read so a record taken before 2026-09-09
            # explains itself. A pooled pass never writes one: a row that loses
            # its cluster's seat to a sibling is refused by the `location` rule
            # above, which names the sibling and the fold it happened under.
            entry = absorbed.get(str(row["location"]))
            taker = None if entry is None else by_picture.get(str(entry["lost_to_picture"]))
            row["competitor"] = _competitor(
                None if taker is None else taker.key, held, order, why, placed
            )
            if row["competitor"] is not None:
                # The DISTANCE is what decided this card and `_dress`'s p_fine gap
                # is not — the two places never competed for a seat. Both go on
                # it: the gap is the finding, since the pre-selection walks on the
                # coarse key and so folds a place the fine head reads higher about
                # two times in five. See GALLERY.md's *Where the coarse key still
                # decides*.
                row["competitor"]["distance"] = round(float(entry["distance"]), 6)
                row["competitor"]["radius"] = float(record["preselection"]["radius"])
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
        "refused_by_a_seat_the_pass_later_moved": len(vacated),
        "refused_by_a_seat_the_pass_later_moved_is": "the record's refusal map is the rule "
        "that refused a row THE LAST TIME IT WAS OFFERED, and the search is anytime — so a "
        "swap or an augmenting chain can eject the seat that refused it afterwards, and the "
        "final state refuses it by nothing. Both are right; they are answers about two "
        "moments. These cards have no competitor to name and say so",
        "moved": vacated,
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


def _refolded(candidates: list, absorbed: dict, preselection: dict, log=print) -> list:
    """`candidates` carrying the cluster the record's own fold put them in.

    A pooled record seats **one wallpaper per cluster**, and the cluster lives on
    [`solve.Candidate.cluster`] — which [`solve.pool`] never sets, because the
    fold is a stage of the solve and not a fact about a ledger row. So a state
    rebuilt from the bare pool answers the one-seat rule over *places*, and every
    row whose cluster's seat went to a sibling at another place comes back
    unrefused or refused by the wrong rule.

    Read off `preselection.folds` and never re-derived: this pool is not the pool
    that pass ran over, so re-running the walk could fold a place the pass did not.

    **Only where that pass POOLED.** A destructive fold deleted its absorbed
    places, so their rows were never in the seating at all and are excluded from
    the proof below by name — relabeling them would be describing a pass that did
    not happen. A record with no `fold` on its pre-selection deleted, which is
    what [`distinct.POOL`] says of itself.
    """
    from dataclasses import replace

    from fractal_wallpapers.curation import distinct

    if str(preselection.get("fold") or distinct.DELETE) != distinct.POOL or not absorbed:
        return candidates
    into = {place: str(entry["lost_to"]) for place, entry in absorbed.items()}
    out = [
        candidate
        if str(candidate.location) not in into
        else replace(candidate, folded_into=into[str(candidate.location)])
        for candidate in candidates
    ]
    log(
        f"[competitors] the record's own fold is re-applied: {len(into):,} absorbed "
        f"place(s), {sum(1 for row in out if row.cluster != row.location):,} row(s) "
        "relabeled onto their cluster before the state is rebuilt"
    )
    return out


#: What the `p_fine` difference on a paired card is, said on the card itself.
#:
#: ⚠ **It was called `gap` until 2026-09-09 and that name was a lie**, measured
#: rather than suspected — `forced_seating_20260909`, Part A. It reads as *how
#: close this row came to a seat* and it is nothing of the kind: the rule that
#: took the row compared no scores at all. `cell_allowance` is a **count** against
#: an allowance, `location` is a seat standing in a cluster, and the competitor
#: shown beside either is picked **after the fact** as the marginal seat — the
#: two rows never met. 127 of that record's 173 paired cards carried a NEGATIVE
#: value, which reads as *I scored higher and still lost* and is simply what a
#: rule that never looked at a score does.
#:
#: So the column is named for what it is — the difference between two readings —
#: and the fact that explains a negative one goes on the card beside it:
#: [`_competitor`]'s `leg`. Of those 105 negative `cell_allowance` competitors,
#: **zero** were placed by the ranked walk; 47 came from `swap`, 47 from
#: `augment`, 11 from a mode floor's mandate. A seat placed by a leg the rank key
#: does not order is a seat that outscoring proves nothing about.
P_FINE_DELTA_IS = (
    "competitor.p_fine minus this row's, and NOT a measure of how close this row came to a "
    "seat. The rule that refused it compared no scores: `cell_allowance` is a count against "
    "an allowance and `location` is a seat standing in a cluster, and the competitor beside "
    "it is the marginal seat picked after the fact. A negative value is normal and means "
    "only that a higher-reading row lost to a rule that never read either — see `leg`, "
    "which names how that seat was placed"
)


def _dress(paired: list, distinct: set) -> None:
    """Give every competitor the palette and `p_fine` its caption needs.

    One keyed ledger read and one pool-scores read for the whole page, because a
    competitor is a *seat* and a page's cards share far fewer of them than it has
    cards — 173 over 77 on the gallery-grade population, 453 over 116 on the
    three-store one it replaced — so a lookup per card would read the same rows
    several times over.

    **Both readings and their difference go on the card, under a name that
    cannot be read as closeness** — see [`P_FINE_DELTA_IS`]. A refusal whose
    competitor reads 0.01 above it and one whose competitor reads 0.4 above it
    are different findings and a page naming only the winner would flatten them;
    a page calling the subtraction a *gap* invites the reader to conclude the
    thing the seating never measured.
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
        rival["p_fine_delta"] = (
            None if rival["p_fine"] is None or mine is None else round(rival["p_fine"] - mine, 6)
        )
        rival["p_fine_delta_is"] = P_FINE_DELTA_IS


def _fold(row: dict, held: dict, absorbed: dict, preselection: dict) -> None:
    """Decorate a `location` card whose seat is at **another place**, in place.

    That happens only under `distinct.POOL`, and it is what the retired
    `solve.SAME_PLACE` card was trying to be: the row did not lose to a stronger
    row at its own place, it lost to a sibling in the near-duplicate cluster the
    pre-selection folded the two into. So the card names the cluster and how far
    each of the two places sits from the place the cluster is seated under.

    ⚠ **A `location` card and NO OTHER**, and the caller holds that. It ran on
    `cell_allowance` cards too until 2026-09-09, where the competitor is the
    marginal seat in a full cell and has nothing to do with the row's cluster:
    the card then named the cluster the row's own place was folded into, gave the
    competitor a `competitor_distance` of 0.0 for not being folded at all, and
    read as *these two are near-duplicates* about two rows at unrelated places.
    Eleven of `20260909T173957Z`'s 120 `cell_allowance` cards carried it, nine of
    them with that zero, and it is what made `57375f0818032399` read as sharing a
    cluster with a seat at a different partition.

    **Both distances are to the cluster's own survivor and neither is the gap
    between the two places**, which the walk never measures: [`distinct.suppress`]
    compares a place against kept places only, so a sibling pair is two spokes of
    one star and the record holds the spokes.
    """
    taker = held.get(str((row.get("competitor") or {}).get("key")))
    if taker is None or str(taker.location) == str(row["location"]):
        return
    mine = absorbed.get(str(row["location"]))
    theirs = absorbed.get(str(taker.location))
    cluster = (mine or theirs or {}).get("lost_to")
    if cluster is None:
        return
    row["competitor"]["cluster"] = str(cluster)
    row["competitor"]["distance"] = 0.0 if mine is None else round(float(mine["distance"]), 6)
    row["competitor"]["competitor_distance"] = (
        0.0 if theirs is None else round(float(theirs["distance"]), 6)
    )
    row["competitor"]["radius"] = float(preselection["radius"])
    row["competitor"]["distance_is"] = (
        "each place's neutral distance to the place its cluster is seated under, and 0 for "
        "that place itself. The two places were never compared with each other: the "
        "pre-selection walk only ever measures a place against places it has already kept"
    )


def _refusing_set(state, candidate, why: str) -> set:
    """The seats the rule that refused this candidate would accept a departure from.

    Mirrors [`rules.State.counted_refusal`]'s own loop so the set belongs to the
    rule that actually acted and not to some later one the candidate also fails:
    the cell taken is the **first** over-full cell in the candidate's own order,
    which is the cell `counted_refusal` returned on.
    """
    if why == "location":
        held = state.places.get(candidate.cluster)
        return set() if held is None else {held}
    for cell in candidate.cells:
        if len(state.cells.get(cell, ())) + 1 > state.rule.allowed(cell, state.n):
            return set(state.cells.get(cell, ()))
    return set()


def _on_disk(store) -> set:
    """Every key this store already has a label-geometry picture for."""
    return {path.stem for path in pictures_dir(store).glob("*.jpg")}


def _marginal(could: set, held: dict, order, why: str, placed: dict) -> dict | None:
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
    return _competitor(ranked[0], held, order, why, placed, alternatives=len(could))


def _competitor(key, held: dict, order, why: str, placed: dict, alternatives: int = 1):
    """One competitor, as the card shows it.

    **`leg` is on it and is the fact a reader needs**, off the record's own
    `seated_for` through [`solve.leg_of`]. It is what explains the card the
    subtraction beside it cannot: a competitor placed by `swap`, `augment` or a
    mandate was placed by a leg the rank key does not order — the swap and the
    chain accept on the lexicographic objective, and a mandate walks its own
    subpool scarcest-first — so a refused row reading higher than it is the
    ordinary case rather than an anomaly. See [`P_FINE_DELTA_IS`].
    """
    from fractal_wallpapers.curation import solve

    candidate = held.get(str(key or ""))
    if candidate is None:
        return None
    why_seated = placed.get(str(candidate.key))
    return {
        "key": str(candidate.key),
        "why": why,
        "how": PAIRING[why],
        "alternatives": int(alternatives),
        "value": float(solve.value_of(candidate, order)),
        "mode": str(candidate.mode),
        "location": str(candidate.location),
        "seated_for": why_seated,
        "leg": None if why_seated is None else solve.leg_of(why_seated),
        "leg_is": "which leg of the pass placed this seat, off the record's own "
        "`seated_for`. `general_pool` is the ranked walk and is the ONLY leg the seating "
        "key ordered; `swap` and `augment` accept on the lexicographic objective and a "
        "mandate walks one demand's subpool scarcest-first, so a seat from any of those "
        "three says nothing about how the two rows would have compared",
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
 .leg { color: #f0b45e; font-weight: 600; }
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


def page(store=None, migration_store=None, repaired_seats_of=None, against=None, log=print) -> dict:
    """One card per wallpaper, in rung order, `p_fine` ascending inside each rung.

    Ascending because the head's largest disagreements with a person come first:
    a picture somebody called a 4 and the pipeline scored near zero is the row
    worth looking at, and a page sorted the other way buries every one of them.

    `migration_store` names a `label_migration` store whose staged scores stand in
    where production has none. A rung-0 or rung-1 row was never read by the fine
    head — that is what the rung *means* — so the column would otherwise be blank
    exactly where the disagreement is largest. It is marked as the migration's
    reading on every card that uses one and never mixed into the pool's column.

    `against` names an earlier store of this same leg, and the page then says how
    many rungs moved between the two records and which way — [`movement`].
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
    moved = movement(rows, against)
    legend = _legend(rows, counts, staged, repaired, moved)
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
        # The store is in the title, because the population is the claim: a page
        # headed "every wallpaper graded 4" over one store of three would be
        # overstating its own reach in its first line.
        title=f"what became of every {STORE} wallpaper graded {GRADE}",
        heading=f"What became of every <b>{STORE}</b> wallpaper graded {GRADE}",
        nav="",
        body=f'<p class="lede">{_lede(rows, read)}</p>'
        f'<div class="legend"><ul>{legend}</ul></div>{_index(rows, counts, slices)}'
        f"{_moved_table(moved)}",
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
        "movement": moved,
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
            f"each card is paired with {PAIRING.get(why, 'nothing')}. {P_FINE_DELTA_IS}",
            by_rule=True,
        )
    return out


def _sorted(rows, keep) -> list:
    mine = [row for row in rows if keep(row)]
    mine.sort(key=lambda row: (row.get("p_fine") is None, row.get("p_fine") or 0.0, row["key"]))
    return mine


def _cut(mine: list, stem: str, heading: str, note: str, by_rule: bool) -> list:
    """One rung's pages, and **none at all for a rung nobody is on**.

    An empty rung used to get one empty page and an index link into it, which was
    invisible while every rung had rows. The gallery-grade population empties two
    of them by construction — that sitting was drawn from the pool, so nothing is
    off the roster or below the coarse bar — and a link promising cards to a reader
    who then finds none is worse than a count with no link. The index still carries
    the count, so the rungs go on adding to the population.
    """
    if not mine:
        return []
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
    #: An em dash where a rung has no page, which is a rung nobody is on — see
    #: [`_cut`]. The count is still the count.
    links = " ".join(f'<a href="{one["file"]}">{one["page"]}</a>' for one in mine) or "—"
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

    A folded place is a third caption and not a wording tweak: nothing *beat* the
    row, its whole place was absorbed before a seat existed, so the caption says
    that and carries the distance the fold was taken at.
    """
    if row.get("rung") == REFUSED:
        rival = row.get("competitor")
        if rival is None:
            return None, None
        if rival.get("distance") is not None:
            return str(rival["key"]), f"absorbed this place · {rival['distance']:.4f} apart"
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


def movement(rows, against) -> dict | None:
    """How this reading's rungs stand against an earlier store's. `None` for none named.

    A rung is a fact about a row *and a record together*, so two readings of the
    same population against two solves are the only way to say a wallpaper's fate
    changed rather than that the page was rebuilt. `against` names an earlier
    [`store_root`] — its `population.jsonl` for the rungs and its `fates.json` for
    the stamp those rungs were read against, so the page can name the record it is
    comparing with instead of asking a reader to remember.

    **Forward is [`RUNG_ORDER`] and nothing else**: a row that was below the fine
    bar and is now refused got *further* before something stopped it, which is
    movement forward even though it still holds no seat. That is the honest
    reading — the rungs are a sequence a picture walks, not a ranking of outcomes
    — and it means `seated` is the only forward move anybody would call good news.

    Rows the earlier store did not hold are counted as `unmatched` rather than as
    movement. The two readings are of the same store, so a mismatch means
    the population itself moved and that is a different finding from a rung
    changing.
    """
    if not against:
        return None
    was = {
        str(row["key"]): row.get("rung")
        for row in _read_jsonl(store_root(against) / POPULATION_NAME)
    }
    if not was:
        raise FateRefused(
            f"no {POPULATION_NAME} in {store_root(against)}, so there is no earlier reading "
            "to compare rungs against."
        )
    read = _read_json(store_root(against) / FATES_NAME)
    moved: dict = {}
    forward = back = same = unmatched = 0
    for row in rows:
        before = was.get(str(row["key"]))
        now = row.get("rung")
        if before is None or now is None:
            unmatched += 1
            continue
        if before == now:
            same += 1
            continue
        moved[f"{before} -> {now}"] = moved.get(f"{before} -> {now}", 0) + 1
        if RUNG_ORDER[now] > RUNG_ORDER[before]:
            forward += 1
        else:
            back += 1
    return {
        "against": str(store_root(against)),
        "against_stamp": read.get("stamp"),
        "compared": len(rows) - unmatched,
        "unmatched": unmatched,
        "unchanged": same,
        "changed": forward + back,
        "forward": forward,
        "back": back,
        "forward_is": "further along RUNGS before something stopped it — `seated` is as "
        "far as forward goes, and every other forward move still holds no seat",
        "transitions": dict(sorted(moved.items(), key=lambda pair: -pair[1])),
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
        delta = against.get("p_fine_delta")
        beside = [
            f'<span><span class="lab">against</span> '
            f"{_mode(against.get('mode', ''), against.get('mode_params') or {})}</span>",
            f'<span><span class="lab">palette</span> {against.get("colormap", "")}</span>',
            f'<span><span class="lab">p_fine</span> {_score(against.get("p_fine"))}</span>',
        ]
        # THE FACT THAT EXPLAINS THE CARD, and it goes ahead of the subtraction
        # rather than after it: a competitor placed by `swap`, `augment` or a
        # mandate was placed by a leg the seating key does not order, so a refused
        # row reading higher than it is the ordinary case. `general_pool` is the
        # only leg the key ordered. See `P_FINE_DELTA_IS`.
        if against.get("leg"):
            beside.append(
                f'<span><span class="lab">seat placed by</span> '
                f'<span class="leg">{against["leg"]}</span>'
                + (
                    ""
                    if against["leg"] == "general_pool"
                    else ' <span class="lab">— a leg the seating key does not order</span>'
                )
                + "</span>"
            )
        if against.get("distance") is not None:
            # The number that actually decided this card. It is a NEUTRAL cosine
            # distance between two places and not a margin between two scores, so
            # it is named in full rather than left to read as one.
            radius = against.get("radius")
            beside.append(
                f'<span><span class="lab">neutral distance</span> '
                f'<span class="gap">{against["distance"]:.4f}</span>'
                + (
                    ""
                    if radius is None
                    else f' <span class="lab">inside the {radius:g} radius, so the two '
                    "count as one place</span>"
                )
                + "</span>"
            )
        if delta is not None:
            beside.append(
                # SIGNED, and the sign is the finding rather than a detail: the
                # marginal seat in a full cell is by definition the weakest seat
                # in it, so it is usually WORSE on p_fine than the row it refused
                # — 326 of 453 on this page. A `+` glued on the front would have
                # printed `+-0.1638` and buried that behind what reads as a typo.
                #
                # ⚠ NAMED `p_fine Δ` AND NEVER `gap`, since 2026-09-09. The
                # old label read as how close this row came to a seat, which is a
                # quantity no rule here computed — see `P_FINE_DELTA_IS`, which the
                # page also states once at the top of every slice.
                '<span><span class="lab">p_fine Δ</span> '
                f'<span class="gap">{delta:+.4f}</span> '
                '<span class="lab">not a margin — nothing compared the two</span></span>'
            )
        if against.get("alternatives", 1) > 1:
            beside.append(
                f'<span class="lab">marginal of {against["alternatives"]} seats the rule '
                "would take a departure from</span>"
            )
        # `"enough" in against` and not `rung == REFUSED`: the question is only
        # ever asked of the two COUNTED rules, so a twin or a folded place would
        # otherwise be told a second rule refused it when nothing of the kind was
        # computed about it.
        if "enough" in against and not against["enough"]:
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

    **Three different silences and the card must not blur them.** A place the
    record simply does not hold; an old destructive fold whose record carries no
    refusal row naming the place that absorbed this one; and a counted refusal
    whose seat the pass **later moved**, where the record and the rebuilt final
    state are both right about two different moments — see [`competitors`]'
    `refused_by_a_seat_the_pass_later_moved`.
    """
    from fractal_wallpapers.curation import solve

    if row.get("rung") != REFUSED:
        return "no seat at this place<br><small>the record holds nothing here</small>"
    if row.get("explained") == solve.SAME_PLACE:
        return (
            "no row to name<br><small>nothing in the pass's own state beat this row, and "
            "no refusal on the record names a place that absorbed it</small>"
        )
    return (
        "no row to name<br><small>nothing in the pass’s FINAL state beat this row: the "
        "record names the rule that refused it the last time it was offered, and the seat "
        "that did was swapped away afterwards. Both are true, of two different "
        "moments</small>"
    )


def _lede(rows, read: dict) -> str:
    return (
        f"<b>{len(rows):,}</b> wallpapers a person graded <b>{GRADE}</b> in the "
        f"<b>{STORE}</b> store, every one of them a ledger row by key since "
        "<code>label-migration merge</code>, so what follows is each one's <em>exact</em> "
        f"fate in <b>{read.get('stamp')}</b> and not an inference from a distribution. "
        "Four rungs and the one before them; a picture stops at the first that holds it. "
        "<em>Each card shows the graded picture beside whatever holds its place</em>, both "
        "drawn fresh at the geometry it was judged at and a wallpaper ships at. Sorted by "
        "<b>p_fine ascending</b> inside each rung, so the largest disagreements come "
        "first — and <em>p_fine is recognition for every row here</em>, the population "
        "being the fine head’s own corpus. "
        "<b>The two finished-render corpora are not on this page</b> and came off it on "
        "2026-09-09: whether a coarse-store 4 is a gallery-grade 4 is unanswered, and that "
        "is a different question from what became of a wallpaper this pool holds."
    )


def _moved_table(moved) -> str:
    """Every rung transition since the earlier record, largest first. `""` for none."""
    if not moved or not moved["transitions"]:
        return ""
    held = "".join(
        f"<tr><td><b>{_title(pair.split(' -> ')[0])}</b> → "
        f'<b>{_title(pair.split(" -> ")[1])}</b></td><td class="n">{count:,}</td></tr>'
        for pair, count in moved["transitions"].items()
    )
    return (
        f"<h2>What moved since {moved['against_stamp']}</h2>"
        f'<p class="rung-note">The same wallpapers, read against the earlier record. '
        f"<b>{moved['forward']:,}</b> got further along the rungs and "
        f"<b>{moved['back']:,}</b> stopped earlier; <b>{moved['unchanged']:,}</b> "
        "stood still. Forward is further before something stopped it, so only a move "
        "to <b>SEATED</b> is a wallpaper that now ships.</p>"
        f'<table class="idx">{held}</table>'
    )


def _legend(rows, counts: dict, staged: dict, repaired: set, moved=None) -> str:
    flagged = [row for row in rows if drawn_bare(row, repaired)]
    borrowed = sum(1 for row in rows if row.get("p_fine_from") == "migration")
    gallery = sum(1 for row in rows if gallery_grade.NAME in (row.get("stores") or ()))
    lines = [f"<b>{_title(name)}</b> — {counts.get(name, 0):,}" for name, _ in RUNGS]
    # Said once, plainly, at the top of the legend rather than in a footnote: on
    # THIS page the caveat is not "some of the column is contaminated", it is that
    # the column is recognition for every row, because the population is the head's
    # own corpus. A page that buried that would be inviting `p_fine` to be read as
    # a verdict.
    lines.append(
        '<span class="warn">Every row on this page is inside the fine head’s own '
        f"corpus.</span> All <b>{gallery:,}</b> of them — <b>{FINE_TRAIN}</b> the head was "
        f"fitted on and <b>{FINE_STOPPING}</b> in its stopping slice — so <b>p_fine</b> "
        "here is <b>recognition and not a reading of an unseen picture</b>. It is what "
        "orders the page and it is not a verdict; the human grade beside it is the only "
        "independent thing on a card. <b>p_ge4</b> is the render judge on the candidate "
        "and is a different head on a different question."
    )
    lines.append(
        "<b>So this is a page about fate, not about accuracy.</b> What a card asks is "
        "which rung stopped a wallpaper a person wanted and what took its place — a "
        "question the record answers exactly. How well either head would score an unseen "
        "picture is not a question this population can be asked."
    )
    if borrowed:
        lines.append(
            f'<span class="staged">p_fine marked *</span> is the <b>label-migration</b> '
            f"reading and not the pool's: <b>{borrowed:,}</b> rows here were never read by "
            "the fine head in production, because <code>score-pool</code> runs on "
            "coarse-clears only."
        )
    if moved and moved["changed"]:
        lines.append(
            f"<b>{moved['changed']:,} of these {moved['compared']:,} wallpapers changed "
            f"rung</b> since <b>{moved['against_stamp']}</b> — <b>{moved['forward']:,}</b> "
            f"further along, <b>{moved['back']:,}</b> stopped earlier — and "
            f"<b>{moved['unchanged']:,}</b> did not move. Same population, same rules, a "
            "re-solve against a repaired pool: what a wallpaper's fate is depends on the "
            "record as well as on the wallpaper, and the index has the transitions."
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
    "RUNG_ORDER",
    "SCHEMA",
    "SEATED",
    "WORKERS",
    "PAGE",
    "PAGE_SIZE",
    "NOT_SHOWN",
    "STYLE",
    "SETTINGS_AWARE_SUBTREES",
    "STORE",
    "FINE_TRAIN",
    "FINE_STOPPING",
    "FateRefused",
    "drawn_bare",
    "leg_of",
    "competitors",
    "fates",
    "graded",
    "keys",
    "movement",
    "page",
    "slug",
    "pictures_dir",
    "population",
    "render",
    "store_root",
]
