"""The owned label corpus, and the lineage deal every held-out read is drawn on.

Two things live here and neither of them is a comparison: [`pool`], which is
every row of both finished-render stores that may be fitted on, paired with the
picture it was cast on; and [`assignment`], which deals those rows' *lineages*
into parts so a model can be read on rows whose neighbourhood it never saw.
[`render_dose`], [`render_grade`] and [`render_deploy`] each stand on one or
both, which is why they are here rather than inside any one of them.

## The fold is drawn over LINEAGES, and a lineage is a neighbourhood group

Three units are available and only the coarsest of them is safe.

A **row** leaks outright: one location is judged many times over, in different
modes and palettes, and rows of one place on two sides of a boundary put the same
picture in training and in the test.

A **location** leaks too, and that is the finding this repository has already
paid for: frames a hair apart on one plane are the same picture twice.
[`fractal_wallpapers.labeling.groups`] is what that costs — same plane digit for
digit, seed `c` within a tolerance, overlapping frames — and its connected
components are the near-duplicate neighbourhoods every split and every interval
in this project is already drawn over. So the fold is drawn over those, and the
bootstrap resamples them too.

**Lineage identity is reachable from a stored label row, and no join is needed to
reach it.** A finished-render row carries its whole `family` and `viewport`,
which is exactly what `groups.assign` reads. What such a row does *not* carry is
the walk provenance a deep run means by the word — `ledger|root_id`, which lives
in a harvest ledger and would need a join by location to recover. The two are
different senses of one term; the near-duplicate neighbourhood is the one a split
has to be drawn over, so it is the one used, and this paragraph is here so that a
later reader does not think the other was overlooked.

**The grouping is assigned over the POOLED corpus, not per store.** Groups
holding rows of both kinds carry a large share of everything, so a grouping taken
per store would leak a lineage from the smooth side into the strange side's
training and never say so.

## What the pool leaves out, and what that costs

**The swept rows.** [`SWEPT_BATCH`] served one page ordered by the head's own
`P(>=4)`, and the sweep accepts the suggested tier for every unlabeled row from
the current position to the end. Nothing records which button produced a verdict;
what survives is the bound in `labeling/README.md` — the last override sits at
position [`LAST_OVERRIDE`] and every row after it agrees with the suggestion
exactly. Those rows are the head's own decode restated, so fitting or testing on
them is fitting and testing a model on its own output. They are dropped at the
read, and counted.

**The rows a store should not be holding.** Rows whose mode routes to the other
store sit in the one they arrived in, because they arrived before the writer's
routing guard existed. [`render_train.population`] already derives that exclusion
at the read and this derives it the same way, through the same call.

## The deal is written down, and it is not a band

[`write_assignment`] lands in the regenerable tree, never in a run directory
beside the shipped bands: nothing here is a band and nothing here answers a bar.
A reader that finds no assignment is told to deal one rather than handed a fresh
deal silently, because "read on the same holdout" is a claim two runs can only
make if they read the same file.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.labeling import finished, groups
from fractal_wallpapers.models import finished_train, metrics, render_train, renders
from fractal_wallpapers.paths import under

#: The schema every record here carries.
SCHEMA = 1


class FoldsError(RuntimeError):
    """A pool or a deal that cannot be built on what is here."""


def root() -> Path:
    """Where the deal lives: the regenerable tree, never a run directory."""
    return under("render_folds")


def assignment_path() -> Path:
    return root() / "assignment.json"


#: How many parts the lineages are dealt into, and the seed they are dealt under.
#: Both are part of the assignment's identity and both are written into it. Five
#: parts is a 20% holdout, which is the share a held-out read wants here: enough
#: rows to say something and few enough that the fit still sees the corpus.
FOLDS = 5
FOLD_SEED = 0

#: The swept page, and the last position on it carrying an override. Every unit
#: after this one agrees with the suggestion exactly and is the head's own decode
#: restated rather than a verdict — `labeling/README.md` and
#: `data/batch_caveats.md` carry the derivation.
SWEPT_BATCH = "under_seen_modes"
LAST_OVERRIDE = 269

#: Draws in every interval here, and its seed. The repository's own, so that an
#: interval from this module and one from `render_acceptance` are the same
#: statistic rather than two.
DRAWS, BOOTSTRAP_SEED = 5000, 0


def position_of(row: dict) -> int | None:
    """A row's position on the page that served it, or `None` if it had no page.

    The unit id is the position and is the only place it survives: `u0137` is the
    hundred and thirty-seventh row of its sheet.
    """
    unit = row.get("unit")
    if not isinstance(unit, str) or not unit.startswith("u") or not unit[1:].isdigit():
        return None
    return int(unit[1:])


def swept(row: dict) -> bool:
    """Whether this row is one the sweep filled rather than one a person cast."""
    if row.get("batch") != SWEPT_BATCH:
        return False
    position = position_of(row)
    return position is not None and position > LAST_OVERRIDE


def pool() -> tuple[list[dict], list[render_train.Picture], dict]:
    """Every owned row that may be fitted on, with its picture and what was cut.

    The rows and the pictures are one population in one order: index `i` of each
    is the same verdict, which is what lets the grouping be taken over the rows
    and applied to the pictures.
    """
    rows: list[dict] = []
    pictures: list[render_train.Picture] = []
    absent: list[str] = []
    cut = {"off_kind": 0, "swept": 0}
    per_kind: dict[str, dict] = {}
    forbidden = render_train.pinned_everywhere()

    for kind in render_train.KINDS:
        counted = {"scored": 0, "off_kind": 0, "swept": 0, "kept": 0, "pinned": 0}
        crops = renders.crop_dir(kind)
        # One listing of the crop directory rather than a stat a row: see
        # [`renders.present`] for the measurement. This loop is the pool's whole
        # cost and it runs over every scored row of both stores.
        on_disk = renders.present(kind)
        for row in finished.resolved(kind).scored():
            counted["scored"] += 1
            if finished.routed_to(row["mode"]) != kind:
                counted["off_kind"] += 1
                cut["off_kind"] += 1
                continue
            if swept(row):
                counted["swept"] += 1
                cut["swept"] += 1
                continue
            name = renders.job_name({**row, "_head": kind})
            path = crops / f"{name}.jpg"
            if f"{name}.jpg" not in on_disk:
                absent.append(name)
                continue
            place = finished.place_of(row)
            counted["kept"] += 1
            counted["pinned"] += int(place in forbidden)
            rows.append(row)
            pictures.append(
                render_train.Picture(
                    path=path,
                    score=int(row["score"]),
                    side="train",
                    batch=row["batch"],
                    place=repr(place),
                    partition=row.get("partition") or "",
                    mode=row["mode"],
                    name=name,
                    kind=kind,
                )
            )
        per_kind[kind] = counted

    if absent:
        raise FoldsError(
            f"{len(absent)} judged pictures are not in a render cache (e.g. {absent[:3]}). A "
            f"head's cache has to be complete against its stored rows before it fits: "
            f"`renders plan` then `renders build`, both heads."
        )
    record = {
        "rows": len(rows),
        "cut": cut,
        "per_kind": per_kind,
        "swept_rule": (
            f"{SWEPT_BATCH} positions past {LAST_OVERRIDE} — the last override on a page the "
            f"sweep filled to the end, so every row after it restates the head's own decode"
        ),
        "off_kind_rule": "a row whose mode routes to the other store, derived at the read",
    }
    return rows, pictures, record


def assignment(seed: int = FOLD_SEED, folds: int = FOLDS) -> dict:
    """Deal the lineages into folds, and say exactly what was dealt.

    Groups are shuffled by the seed and then taken in turn by whichever fold
    currently holds the fewest rows, because lineage sizes run from one to
    sixty-odd and a round-robin over a shuffle leaves folds differing by hundreds
    of rows. The result is a function of the seed, the fold count and the corpus,
    so a later run reproduces it — and it is written down anyway, because
    "reproduces" is a claim a reader should not have to take on faith.
    """
    rows, pictures, record = pool()
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise FoldsError(
            f"{grouping.n_unplaced} rows carry no location identity, so they cannot be "
            f"grouped. A fold quietly holding ungrouped rows would leak by exactly the "
            f"amount nobody counted."
        )

    order = sorted(grouping.members)
    random.Random(seed).shuffle(order)
    sizes = [0] * folds
    fold_of_group: dict[int, int] = {}
    for group in order:
        smallest = min(range(folds), key=lambda index: (sizes[index], index))
        fold_of_group[group] = smallest
        sizes[smallest] += len(grouping.members[group])

    fold_of_row = [fold_of_group[group] for group in grouping.of_row]
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    per_fold = []
    for fold in range(folds):
        members = [index for index, where in enumerate(fold_of_row) if where == fold]
        per_fold.append(
            {
                "fold": fold,
                "rows": len(members),
                "groups": sum(1 for where in fold_of_group.values() if where == fold),
                "places": len({pictures[index].place for index in members}),
                "kinds": {
                    kind: sum(1 for index in members if pictures[index].kind == kind)
                    for kind in render_train.KINDS
                },
                "tiers": finished_train.histogram([pictures[index] for index in members]),
                "pinned_rows": sum(1 for index in members if pictures[index].place in pinned),
            }
        )

    return {
        "schema": SCHEMA,
        "seed": seed,
        "folds": folds,
        "rule": (
            "connected components of the near-duplicate neighbourhood rule over the POOLED "
            "corpus, shuffled by the seed and taken by the fold holding the fewest rows"
        ),
        "unit": (
            "lineage — labeling.groups.assign, the same unit every split and every interval "
            "in this repository is drawn over"
        ),
        "population": record,
        "grouping": grouping.summary(),
        "per_fold": per_fold,
        "fold_of_row": fold_of_row,
        # The lineage each row was grouped into, carried so that every arm's
        # out-of-fold rows resample the SAME clusters. Group ids are assigned
        # over whichever population was current when they were made, so a read
        # that re-derived them per arm would draw its interval over a partition
        # nobody holds.
        "group_of_row": [int(group) for group in grouping.of_row],
    }


def write_assignment(seed: int = FOLD_SEED, folds: int = FOLDS) -> tuple[Path, dict]:
    """Derive the folds and write them down. What every arm afterwards reads."""
    document = assignment(seed, folds)
    path = assignment_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path, document


def read_assignment() -> dict:
    path = assignment_path()
    if not path.is_file():
        raise FoldsError(
            f"{path} does not exist — derive the folds before fitting on them, so that every "
            f"arm is fitted on one partition rather than on its own."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def sides_for(fold: int, document: dict | None = None, population: tuple | None = None):
    """The population with every picture on the side this fold puts it.

    Four sides, and they are [`render_train`]'s own. The fold's own lineages are
    `eval` — the out-of-fold rows this model is read on. A pinned row anywhere
    else is `excluded`: it may not train, ever, and it is not this fold's test
    either. Everything else trains, and the selection slice is drawn out of that
    afterwards by the recipe's own rule at the recipe's own share and seed, over
    places, so that a place cannot straddle.

    `population` is [`pool`]'s own return value, passed in by a caller that
    already holds one. Building it sweeps both stores and digests a recipe per
    row, and a caller asking about several folds would otherwise pay that once
    per fold — every picture's side is reassigned here on every call, so one
    population answers for all five.
    """
    document = document or read_assignment()
    rows, pictures, record = population or pool()
    fold_of_row = document["fold_of_row"]
    if len(fold_of_row) != len(pictures):
        raise FoldsError(
            f"the written assignment covers {len(fold_of_row)} rows and the corpus now holds "
            f"{len(pictures)}. The store grew under the folds: re-derive them and re-fit every "
            f"arm, or the arms are not comparable."
        )
    pinned = {repr(place) for place in render_train.pinned_everywhere()}

    for picture, where in zip(pictures, fold_of_row, strict=True):
        if where == fold:
            picture.side = "eval"
        elif picture.place in pinned:
            picture.side = render_train.EXCLUDED
        else:
            picture.side = "train"

    training = [picture for picture in pictures if picture.side == "train"]
    places = sorted({picture.place for picture in training})
    draw = random.Random(render_train.SELECTION_SEED)
    draw.shuffle(places)
    chosen = set(places[: max(1, round(len(places) * render_train.SELECTION_SHARE))])
    for picture in training:
        if picture.place in chosen:
            picture.side = render_train.SELECTION

    split = {
        "fold": fold,
        "of_folds": document["folds"],
        "seed": document["seed"],
        "rule": (
            "the fold's own lineages are the out-of-fold test; a location pinned to either "
            "blind sheet never trains and is excluded outside its own fold; everything else "
            "trains"
        ),
        "unit": document["unit"],
        "population": record,
        "pinned_locations_union": len(pinned),
        "excluded_pictures": sum(1 for p in pictures if p.side == render_train.EXCLUDED),
        "test_pictures": sum(1 for p in pictures if p.side == "eval"),
        "selection": {
            "share": render_train.SELECTION_SHARE,
            "seed": render_train.SELECTION_SEED,
            "drawn_over": "places on this fold's training side, so a place cannot straddle",
            "places": len(chosen),
            "of_places": len(places),
            "pictures": sum(1 for p in pictures if p.side == render_train.SELECTION),
        },
    }
    return rows, pictures, split


def top_cutpoint_loss(labels, probabilities, classes: int) -> float:
    """The TOP cutpoint's own cross-entropy, as an epoch-selection objective.

    The shipped rule averages the cross-entropy of all three cutpoints, and on
    this corpus the bottom one decides where the run stops: the shipped band
    picks epoch four or five of forty and the baseline arm here picked **two**,
    while `AUC(>=4)` on the very same selection slice goes on improving to epoch
    eleven or thirteen every time. So the head is stopped where the `>=2`
    cutpoint is happy, and ordering the top is what it is for.

    It is the same proper scoring rule read at one cutpoint rather than three —
    [`metrics.cutpoint_cross_entropy`] over a two-tier framing of the top
    boundary — so there is one implementation of it and not two.
    """
    import numpy

    top = numpy.where(numpy.asarray(labels) >= classes, 2, 1)
    return metrics.cutpoint_cross_entropy(top, numpy.asarray(probabilities)[:, [classes - 2]], 2)
