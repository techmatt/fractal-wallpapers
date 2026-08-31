"""Grouped cross-validation for the render judge: the folds, the arms, the read.

The shipped judge is a **gate rather than a top-end ranker**. Inside `P(>=4)` in
[0.60, 0.95) its score barely orders a human's 3-against-4 verdict: four
calibration strata put the realized slope five to seven times flatter than the
design assumed, and nine under-seen modes said it again at `AUC(>=4) = 0.62` over
269 hand-cast rows. Working around that has been tried; a retrain is the only
thing that can fix it. What this module is for is the evidence a retrain needs,
and it is the ordinary train-test discipline rather than a fresh instrument:
**a grouped holdout over rows this project already owns**, with the groupings
this corpus actually needs.

## This is a SCREEN, and its asymmetry is the first thing to say about it

The deal is five ways, which is a 20% holdout per part, and this run fits **one**
of them — [`HOLDOUT_FOLD`]. The other four are what an adoption run would fill
in, and the artifacts are shaped so that it can, without re-deriving anything.

What the screen answers is narrow: *can anything rank the top at all, and roughly
by how much*. It is not the adoption bar, which stands for a later run on
whichever arm survives here. With about 200 fours in the strange store a 20%
holdout leaves about forty of them, and the motivating slice is band-restricted
on top of that — so **a positive result here is informative and a null one is
not**. Every read this module writes carries the positive and negative counts
inside the slice for exactly that reason: that pair is what says whether a null
was worth anything.

## Nothing here adopts anything

No weights ship, no scoring head moves, no floor is restated. Every fold trains
into the regenerable tree and is read there. Adoption is a later decision, taken
by a person against a bar declared before any number existed.

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

**The grouping is assigned over the POOLED corpus, not per store.** 295 groups
hold rows of both kinds and those groups carry 4,181 rows — nearly half of
everything — so a grouping taken per store would leak a lineage from the smooth
side into the strange side's training and never say so.

## What is left out, and what that costs

**The swept rows.** `under_seen_modes` served one page of 504 ordered by the
head's own `P(>=4)`, and the sweep accepts the suggested tier for every unlabeled
row from the current position to the end. Nothing records which button produced a
verdict; what survives is the bound in `labeling/README.md` — the last override
sits at position [`LAST_OVERRIDE`] and every row after it agrees with the
suggestion exactly. Those rows are the head's own decode restated, so fitting or
testing on them is fitting and testing a model on its own output. They are
dropped here at the read, and counted.

**The rows a store should not be holding.** Forty `smooth`-routed rows sit in the
strange store because they arrived before the writer's routing guard existed.
[`render_train.population`] already derives that exclusion at the read and this
derives it the same way, through the same call.

A third exclusion is named in the prompt this work was cut from — retired
three-class rows carrying a null `P(>=4)` — and **nothing is dropped for it,
because it is not a label-store fact.** It belongs to the candidate pool, where
125 release rows were judged by an artifact that had no fourth tier; see
[`fractal_wallpapers.curation.rescore`]. No label row carries a `p_ge4` column at
all, so there is nothing here to apply it to.

## The pin is obeyed rather than worked around

`blind_minibrot` and `blind_modes` are pinned evaluation sides and a pinned row
may never train. A fold cannot be allowed to contradict that, so a pinned row is
**test-side in the fold that owns its lineage and excluded everywhere else** —
which is the [`render_train.EXCLUDED`] side that already exists for a row pinned
in the other store. Every pinned row still receives exactly one out-of-fold
reading, from a model that never saw it, and the trainer's own pin guard is left
armed and passes untouched. Nothing is registered and nothing is contradicted:
these folds are an analysis construct derived at read time, and no code path here
opens the registry for writing.

## The recipe is the trainer's, and this module owns no second copy of it

Arm A is the shipped recipe refit on these folds, and it is a refit rather than a
read of the shipped artifact for one reason: that artifact trained on most of
these rows, so its scores on them are in-sample and would flatter it. The refit
runs through [`render_train.run`] itself — the same loop, the same selection
objective, the same records — reached by that function's `split` and `directory`
arguments. A baseline that was a re-typed trainer would measure the re-typing.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.labeling import finished, groups
from fractal_wallpapers.models import (
    finished_train,
    head,
    metrics,
    render_train,
    renders,
    train,
)
from fractal_wallpapers.paths import under

#: The schema every record here carries.
SCHEMA = 1

#: How many parts the lineages are dealt into, and the seed they are dealt under.
#: Both are part of the assignment's identity and both are written into it. Five
#: parts is a 20% holdout, which is what the screen wanted; dealing all five and
#: fitting one keeps the rest available to an adoption run at no design cost.
FOLDS = 5
FOLD_SEED = 0

#: The part this screen holds out and reads on. The other four are dealt and left
#: unfitted, and every record here says which parts it actually covers rather
#: than implying the whole deal.
HOLDOUT_FOLD = 0

#: The swept page, and the last position on it carrying an override. Every unit
#: after this one agrees with the suggestion exactly and is the head's own decode
#: restated rather than a verdict — `labeling/README.md` and
#: `data/batch_caveats.md` carry the derivation.
SWEPT_BATCH = "under_seen_modes"
LAST_OVERRIDE = 269

#: The band the motivating slice is cut on: where the shipped judge is a gate and
#: not a ranker. Half-open, and read on the **baseline arm's own out-of-fold**
#: `P(>=4)`, so every arm is judged on one population rather than on its own top.
MOTIVATING_BAND = (0.60, 0.95)

#: Draws in every interval here, and its seed. The repository's own, so that an
#: interval from this module and one from `render_acceptance` are the same
#: statistic rather than two.
DRAWS, BOOTSTRAP_SEED = 5000, 0


class CrossValidationError(RuntimeError):
    """A fold that cannot be built, fitted or read on what is here."""


def root() -> Path:
    """Where the folds live: the regenerable tree, never a run directory.

    Fifteen fold directories beside the shipped bands would read as fifteen
    registered runs. Nothing here is a band and nothing here answers a bar, so it
    lands where every other derived thing lands.
    """
    return under("render_cv")


def arm_dir(arm: str) -> Path:
    return root() / arm


def fold_dir(arm: str, fold: int) -> Path:
    return arm_dir(arm) / f"fold{fold}"


def assignment_path() -> Path:
    return root() / "assignment.json"


def out_of_fold_path(arm: str) -> Path:
    return arm_dir(arm) / "out_of_fold.jsonl"


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
        raise CrossValidationError(
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
        raise CrossValidationError(
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
        raise CrossValidationError(
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
        raise CrossValidationError(
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


#: The selection objectives an arm may name, and what each one is. A fold's own
#: config records the sentence rather than the key, so a written fold says which
#: rule chose its epoch without anyone having to hold this table.
SELECTION_OBJECTIVES: dict[str, dict] = {
    "top_cutpoint": {
        "objective": top_cutpoint_loss,
        "says": (
            "min cross-entropy of the TOP cutpoint's own unconditional probability over the "
            "selection slice, through the deploy transform. The shipped rule averages all "
            "three cutpoints and is decided by the bottom one; this reads only the boundary "
            "the supply engine acts on"
        ),
    },
}

#: What the arms are **not**, and why — because a menu item ruled out by records
#: that already exist is worth more written down than re-measured.
#:
#: * **Reweighting the top boundary, in any of its forms, is close to spent.**
#:   [`head.corn_loss`] already averages each cutpoint's *own mean*, so the `>=4`
#:   subtask carries a third of the loss however few fours there are, and its
#:   conditional subset is about 57% of a sampled batch rather than a sliver. The
#:   sampler's square-root balance already lifts tier 4 from 9.4% of rows to
#:   21.4% of sampled mass — 2.28x of the 2.67x a full inverse-frequency balance
#:   could give. And a CORN classifier is one `Linear`, whose rows do not
#:   interact, so the top cutpoint already has its own last layer. What is shared
#:   is the trunk, and the lever on that is not a weight.
#: * **Backbone capacity is ruled out by three runs already on disk.** The
#:   [`render_train.MISLAUNCHED`] band is the medium backbone — 3.3x the
#:   checkpoint — trained on this same corpus, and its peak selection-slice
#:   `AUC(>=4)` is 0.872 / 0.888 / 0.876 against the shipped small backbone's
#:   0.876 / 0.880 / 0.888. The same ceiling at three times the parameters.
#:
#: What that leaves is the half of the capacity question those runs share rather
#: than answer — every one of them read the same 384x224 crop — and the stopping
#: rule, which is the one place the easy boundary still decides something.
RULED_OUT: dict[str, str] = {
    "reweight_the_top_boundary": (
        "CORN already averages per-cutpoint means, the >=4 subset is ~57% of a sampled batch, "
        "the sqrt sampler already lifts tier 4 to 21.4% of sampled mass against a 25% "
        "ceiling, and each cutpoint already owns its own row of the classifier"
    ),
    "backbone_capacity": (
        "the three mislaunched medium-backbone runs are 3.3x the parameters on this corpus "
        "and peak at the same selection-slice AUC(>=4) as the small backbone"
    ),
    "an_arm_for_irreducibility": (
        "there is nothing to build. If 3-against-4 is not in the picture at this geometry, "
        "every arm sits flat at the baseline's number, which is what the table would show"
    ),
}


#: The arms. Each is a whole design plus the backbone it declares, and the
#: backbone is declared here for the reason [`render_train.MISLAUNCHED`] names:
#: `render_train.RECIPE` still carries the FIRST joint candidate's medium, so a
#: launch that does not re-ask the value trains at a backbone no declaration
#: names. Every arm here passes its own value and every fold's written config is
#: checked against it afterwards.
#:
#: `baseline` is arm A: the shipped recipe, unchanged in every key, refit on
#: these folds. It is the comparison, and it doubles as the read on whether this
#: era's new rows bought anything — arm A against the shipped artifact's own
#: history splits rows from scale.
ARMS: dict[str, dict] = {
    "shipped": {
        "artifact": True,
        "backbone": render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        "what": (
            "not an arm and not fitted here — the artifact that serves today, read over the "
            "same held-out rows. IN-SAMPLE: it trained on most of them, so its number on "
            "them flatters it. It is the column that separates rows from recipe"
        ),
    },
    "baseline": {
        "backbone": render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        "seed": 1,
        "what": (
            "arm A — the shipped recipe (the `enlarged_corpus` band: small backbone, "
            "four-class CORN, forty epochs, the pooled cutpoint cross-entropy as the "
            "selection objective) refit unchanged on these folds. The shipped head trained "
            "on most of these rows, so its own scores on them are in-sample; this is what a "
            "fair comparison needs"
        ),
    },
    "top_cutpoint_selection": {
        "backbone": render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        "seed": 1,
        "selection": "top_cutpoint",
        "what": (
            "one key moved: the epoch is chosen by the >=4 cutpoint's own cross-entropy "
            "instead of the mean over all three. The baseline arm stops at epoch 2 of 40 "
            "while AUC(>=4) on its own selection slice peaks at 11, so the shipped rule "
            "leaves top-end ordering on the table by construction"
        ),
    },
    "input_detail": {
        "backbone": render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        "seed": 1,
        "target_dims": [512, 288],
        "what": (
            "one key moved: the picture arrives at 512x288 instead of 384x224. A judged "
            "render is 1280x720 and the head has always read a fourteenth of its pixels; "
            "junk-against-not survives that and a 3-against-4 judgement may not. It is the "
            "half of the capacity question the medium-backbone runs share rather than answer"
        ),
    },
}


def declared_backbone(arm: str) -> str:
    if arm not in ARMS:
        raise CrossValidationError(f"{arm!r} is not an arm here; the arms are {sorted(ARMS)}")
    return str(ARMS[arm]["backbone"])


def check_written_backbone(arm: str, fold: int) -> None:
    """Refuse a fold whose written config did not train at the arm's declaration.

    The other half of the discipline `render_train.check_declared_backbone`
    exists for. A fold directory's `config.json`, its checkpoints' own configs
    and any audit of them all agree with each other, and would agree with a wrong
    value just as readily; the only place that says what the arm was supposed to
    be is this module.
    """
    path = fold_dir(arm, fold) / "config.json"
    if not path.is_file():
        return
    written = str(json.loads(path.read_text(encoding="utf-8")).get("backbone"))
    declared = declared_backbone(arm)
    if written != declared:
        raise CrossValidationError(
            f"arm {arm!r} declares the backbone {declared!r} and fold {fold} trained at "
            f"{written!r}. A fold that realized another design cannot stand in an arm's "
            f"pooled out-of-fold read."
        )


def fit(arm: str, fold: int, device: str = "auto", epochs: int | None = None, log=train.say):
    """Fit one arm on one fold, through the trainer the shipped band used."""
    if arm not in ARMS:
        raise CrossValidationError(f"{arm!r} is not an arm here; the arms are {sorted(ARMS)}")
    entry = ARMS[arm]
    if entry.get("artifact"):
        raise CrossValidationError(
            f"{arm!r} is an artifact that already exists rather than a design to fit — read "
            f"it with `read_shipped` instead."
        )
    document = read_assignment()
    directory = fold_dir(arm, fold)
    directory.mkdir(parents=True, exist_ok=True)

    def split():
        _rows, pictures, record = sides_for(fold, document)
        return pictures, record

    named = entry.get("selection")
    chosen = SELECTION_OBJECTIVES[named] if named else {}
    record = render_train.run(
        device=device,
        epochs=epochs,
        seed=int(entry["seed"]),
        run_name=f"cv_{arm}_fold{fold}",
        backbone=str(entry["backbone"]),
        target_dims=entry.get("target_dims"),
        split=split,
        directory=directory,
        selection=chosen.get("objective"),
        selection_says=chosen.get("says"),
        log=log,
    )
    check_written_backbone(arm, fold)
    return record


def read_out_of_fold(arm: str, fold: int, device: str = "auto", log=train.say) -> dict:
    """Read this fold's held-out rows through its own checkpoint, and write them.

    One row a picture, carrying its whole join and the fold that produced it, so
    the pooled file is a population a later read can cut any way it needs without
    going back to the stores.
    """
    checkpoint = fold_dir(arm, fold) / "best.pt"
    if not checkpoint.is_file():
        raise CrossValidationError(f"{checkpoint} does not exist — fit the fold before reading it")
    document = read_assignment()
    rows, pictures, _split = sides_for(fold, document)
    lineage = document["group_of_row"]
    held = [
        (row, picture, group)
        for row, picture, group in zip(rows, pictures, lineage, strict=True)
        if picture.side == "eval"
    ]
    if not held:
        raise CrossValidationError(f"fold {fold} holds nothing out, so there is nothing to read")

    model, config, where = render_train.load_checkpoint(checkpoint, device)
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    classes = int(config["classes"])
    log(f"{arm} fold {fold}: reading {len(held)} held-out pictures through {checkpoint}")
    probabilities = train.score(
        model, [picture.path for _row, picture, _group in held], transform, where, classes, config
    )

    path = fold_dir(arm, fold) / "out_of_fold.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (row, picture, group), probability in zip(held, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "arm": arm,
                "fold": fold,
                "lineage": int(group),
                "kind": picture.kind,
                "name": picture.name,
                "batch": row["batch"],
                "score": int(row["score"]),
                "partition": row.get("partition"),
                "family": row["family"],
                "viewport": row["viewport"],
                "mode": row["mode"],
                "mode_params": row.get("mode_params") or {},
                "curve": row["curve"],
                "colormap": row["colormap"],
                "recipe": row["recipe"],
                "render": row["render"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"arm": arm, "fold": fold, "rows": len(held), "wrote": str(path)}


def shipped_artifact() -> Path:
    """The artifact that serves today, resolved through the manifest.

    `models/weights.json` is the only thing that answers *what ships*, so the
    read that stands for the incumbent here resolves through it rather than
    naming a file.
    """
    from fractal_wallpapers.paths import repo_root

    manifest = json.loads((repo_root() / "models" / "weights.json").read_text(encoding="utf-8"))
    entry = manifest["heads"][render_train.HEAD]
    path = repo_root() / "models" / render_train.HEAD / entry["asset"]
    if not path.is_file():
        raise CrossValidationError(
            f"{path} is not here — `fractal-wallpapers fetch-weights` brings the shipped "
            f"artifact down, and the incumbent column cannot be read without it."
        )
    return path


def read_shipped(fold: int = HOLDOUT_FOLD, device: str = "auto", log=train.say) -> dict:
    """The shipped artifact's own read of the held-out rows.

    **This column is IN-SAMPLE and is labelled so everywhere it appears.** The
    shipped head trained on most of these rows, so its score on them flatters it,
    which is exactly why the baseline arm is a refit rather than this. It is read
    anyway because it is the only thing that answers the other question: whether
    a difference between the refit and what serves today is about the rows the
    stores have grown or about the recipe. A refit that beats an in-sample
    incumbent has beaten it the hard way.
    """
    document = read_assignment()
    rows, pictures, _split = sides_for(fold, document)
    lineage = document["group_of_row"]
    held = [
        (row, picture, group)
        for row, picture, group in zip(rows, pictures, lineage, strict=True)
        if picture.side == "eval"
    ]
    artifact = shipped_artifact()
    model, config, where = render_train.load_checkpoint(artifact, device)
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    classes = int(config["classes"])
    log(f"shipped fold {fold}: reading {len(held)} held-out pictures through {artifact.name}")
    probabilities = train.score(
        model, [picture.path for _row, picture, _group in held], transform, where, classes, config
    )

    directory = fold_dir("shipped", fold)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "out_of_fold.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (row, picture, group), probability in zip(held, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "arm": "shipped",
                "in_sample": True,
                "fold": fold,
                "lineage": int(group),
                "kind": picture.kind,
                "name": picture.name,
                "batch": row["batch"],
                "score": int(row["score"]),
                "partition": row.get("partition"),
                "mode": row["mode"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"arm": "shipped", "fold": fold, "rows": len(held), "wrote": str(path)}


def folds_read(arm: str) -> list[int]:
    """Which parts of the deal this arm has actually been fitted and read on.

    A screen fits one and an adoption run would fit five, and a record that
    implied the whole deal either way would be the one thing a later reader
    cannot check. So what was covered is derived rather than assumed.
    """
    return sorted(
        int(path.parent.name.removeprefix("fold"))
        for path in arm_dir(arm).glob("fold*/out_of_fold.jsonl")
    )


def pooled(arm: str) -> list[dict]:
    """One arm's held-out read: every row it covers, scored by a model blind to it."""
    covered = folds_read(arm)
    if not covered:
        raise CrossValidationError(
            f"arm {arm!r} has no held-out read yet — fit a part of the deal and read it first"
        )
    out: list[dict] = []
    for fold in covered:
        path = fold_dir(arm, fold) / "out_of_fold.jsonl"
        out += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return out


def write_pooled(arm: str) -> Path:
    """The five folds as one file, in a stable order. What a read opens."""
    rows = sorted(pooled(arm), key=lambda row: (row["kind"], row["name"]))
    path = out_of_fold_path(arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


#: **The bar, and it was written before any number here existed.** One arm has to
#: move and four have to stay put; a strange-side gain that costs the smooth side
#: is not a winner, because one judge scores both kinds.
#:
#: The motivating slice is cut on the **baseline arm's own out-of-fold**
#: `P(>=4)`, never on the arm being judged. A slice cut on each arm's own score
#: would be a different population per arm, and the comparison would be between
#: two populations as much as between two heads.
#:
#: **AUC, and not probability agreement.** CORN's scale is calibrated by the
#: training prior, so a refit moves the whole probability scale by construction
#: and a statistic that reads the scale would report that move as a result. Rank
#: metrics are immune to it. Restating a cut on a new scale is a separate
#: question and is not asked here.
BAR: dict = {
    "motivating": {
        "name": "strange_auc_ge4_in_band",
        "population": (
            "strange rows whose BASELINE out-of-fold P(>=4) falls in the band where the "
            "shipped judge is a gate rather than a ranker"
        ),
        "band": list(MOTIVATING_BAND),
        "statistic": "AUC at the >=4 boundary",
        "requires": "significantly better — the paired interval's lower bound above zero",
    },
    "guards": [
        {
            "name": "strange_auc_ge3",
            "kind": "strange_render",
            "cutpoint": 3,
            "population": "the whole strange out-of-fold population",
        },
        {
            "name": "strange_auc_ge4",
            "kind": "strange_render",
            "cutpoint": 4,
            "population": "the whole strange out-of-fold population",
        },
        {
            "name": "smooth_auc_ge3",
            "kind": "smooth_render",
            "cutpoint": 3,
            "population": "the whole smooth out-of-fold population",
        },
        {
            "name": "smooth_auc_ge4",
            "kind": "smooth_render",
            "cutpoint": 4,
            "population": "the whole smooth out-of-fold population",
        },
    ],
    "guards_require": (
        "not significantly worse — the paired interval's upper bound at or above zero. "
        "Nothing is asked to improve"
    ),
    "significance": (
        "95% paired bootstrap resampling whole LINEAGE GROUPS rather than rows, on pooled "
        "out-of-fold predictions. No per-fold and no per-mode conjunction anywhere in the rule"
    ),
    "descriptive_only": (
        "per-mode and per-fold numbers, reported with n and never used to declare a winner"
    ),
}


def keyed(rows: list[dict]) -> dict[tuple, dict]:
    """One arm's out-of-fold rows by picture identity, for a paired read."""
    return {(row["kind"], row["name"]): row for row in rows}


def aligned(candidate: list[dict], baseline: list[dict]) -> list[tuple[dict, dict]]:
    """The two arms' readings of the same pictures, in one order.

    Refuses rather than intersecting quietly: two arms fitted on one written
    assignment read exactly the same population, so a difference in what they
    cover is a difference in what was fitted and not something to work around.
    """
    mine, theirs = keyed(candidate), keyed(baseline)
    if set(mine) != set(theirs):
        raise CrossValidationError(
            f"the two arms do not cover the same pictures — {len(set(mine) - set(theirs))} only "
            f"in the candidate and {len(set(theirs) - set(mine))} only in the baseline. Both "
            f"arms have to be fitted on one written assignment."
        )
    return [(mine[key], theirs[key]) for key in sorted(mine)]


def _delta(pairs: list[tuple[dict, dict]], cutpoint: int) -> dict:
    """The paired AUC difference at one cutpoint, with its lineage interval.

    An empty population reads `undefined` rather than raising: an arm of the bar
    that has no rows has not measured a bad candidate, it has measured nothing,
    and a zero there would read as agreement.
    """
    import numpy

    if not pairs:
        return {"n": 0, "positives": 0, "lineages": 0, "delta": None, "lo": None, "hi": None}
    labels = numpy.array([int(row["score"]) >= cutpoint for _mine, row in pairs], dtype=float)
    ours = numpy.array([float(mine[f"p_ge{cutpoint}"]) for mine, _theirs in pairs])
    theirs = numpy.array([float(row[f"p_ge{cutpoint}"]) for _mine, row in pairs])
    lineages = numpy.array([row["lineage"] for _mine, row in pairs])
    out = metrics.paired_delta(labels, ours, theirs, lineages, draws=DRAWS, seed=BOOTSTRAP_SEED)
    out["n"] = len(pairs)
    out["positives"] = int(labels.sum())
    out["lineages"] = int(len(set(lineages.tolist())))
    return out


def _verdict(interval: dict, better: bool) -> str:
    """What one arm's interval says, under the rule [`BAR`] declares."""
    lo, hi = interval.get("lo"), interval.get("hi")
    if lo is None or hi is None:
        return "undefined"
    if better:
        return "better" if lo > 0 else "not better"
    return "worse" if hi < 0 else "not worse"


def per_mode(pairs: list[tuple[dict, dict]], cutpoint: int) -> list[dict]:
    """Every mode's own AUC on both arms. **Descriptive, and gates nothing.**

    n runs from a handful to a few hundred here, so a per-mode AUC carries a
    standard error that a conjunction over nine of them would trip on by itself.
    It is reported with its n for exactly that reason.
    """
    import numpy

    modes: dict[str, list] = {}
    for mine, theirs in pairs:
        modes.setdefault(theirs["mode"], []).append((mine, theirs))
    out = []
    for mode in sorted(modes):
        members = modes[mode]
        labels = numpy.array([int(row["score"]) >= cutpoint for _mine, row in members])
        out.append(
            {
                "mode": mode,
                "n": len(members),
                "positives": int(labels.sum()),
                "candidate": metrics.auc(
                    labels, [float(mine[f"p_ge{cutpoint}"]) for mine, _theirs in members]
                ),
                "baseline": metrics.auc(
                    labels, [float(row[f"p_ge{cutpoint}"]) for _mine, row in members]
                ),
            }
        )
    return out


def three_against_four(pairs: list[tuple[dict, dict]]) -> dict:
    """The 3-versus-4 question on its own, over every strange row a person put there.

    **Descriptive, and it is here because of the screen's power rather than
    despite it.** The declared slice is band-restricted on top of a 20% holdout
    and comes to a few dozen rows, so it can only see a large effect. This is the
    same question — does the score order a 3 below a 4 — asked of every strange
    row scored 3 or 4, which is four or five times the rows and no band at all.
    It answers a different question from the declared arm and replaces nothing:
    the band is where a bar would act, and this is where the evidence is.
    """

    members = [(mine, theirs) for mine, theirs in pairs if int(theirs["score"]) in {3, 4}]
    if not members:
        return {"n": 0, "positives": 0, "negatives": 0, "delta": None, "lo": None, "hi": None}
    out = _delta(members, 4)
    out["negatives"] = out["n"] - out["positives"]
    out["what"] = "AUC(>=4) over the strange rows a person scored 3 or 4, unbanded"
    return out


def compare(arm: str, baseline: str = "baseline", band_on: str | None = None) -> dict:
    """One arm against the baseline, on every arm of the bar. **Decides nothing.**

    The verdict column says which arms cleared the bar as it was declared. What
    to do about that is a person's, and no line of this record recommends
    anything.

    **`band_on` names the arm whose score cuts the motivating slice**, and it
    defaults to the reference arm. It is a parameter because the declared cut
    turned out to be unreadable at this holdout size: the baseline arm puts 13
    strange rows in the band where the shipped head puts 43, and 13 rows is not
    a measurement. Naming it makes the population a stated choice instead of a
    consequence of argument order, and a read that moves it says so in the
    record.
    """
    candidate_rows, baseline_rows = pooled(arm), pooled(baseline)
    pairs = aligned(candidate_rows, baseline_rows)
    band_on = band_on or baseline
    cutter = {
        (row["kind"], row["name"]): row
        for row in (baseline_rows if band_on == baseline else pooled(band_on))
    }

    low, high = MOTIVATING_BAND
    in_band = [
        (mine, theirs)
        for mine, theirs in pairs
        if theirs["kind"] == "strange_render"
        and low <= float(cutter[(theirs["kind"], theirs["name"])]["p_ge4"]) < high
    ]
    if not in_band:
        raise CrossValidationError(
            f"arm {band_on!r} puts no strange row in {MOTIVATING_BAND}, so the slice this "
            f"work exists to move is empty."
        )
    motivating = _delta(in_band, 4)
    motivating["verdict"] = _verdict(motivating, better=True)
    # Both counts, always. A null over four positives and a null over four
    # hundred are the same number and different findings, and this is the pair
    # that tells them apart.
    motivating["negatives"] = motivating["n"] - motivating["positives"]
    # Which arm's score cut the band, said out loud. The reference arm defines
    # the population — arm A's band when an arm is read against arm A, and the
    # shipped head's band when arm A is read against what serves today, which is
    # the population the complaint about that head names.
    motivating["band_cut_on"] = band_on

    guards = []
    for entry in BAR["guards"]:
        members = [pair for pair in pairs if pair[1]["kind"] == entry["kind"]]
        interval = _delta(members, int(entry["cutpoint"]))
        interval["verdict"] = _verdict(interval, better=False)
        guards.append({**entry, **interval})

    strange = [pair for pair in pairs if pair[1]["kind"] == "strange_render"]
    return {
        "schema": SCHEMA,
        "candidate": arm,
        "baseline": baseline,
        "declared": ARMS[arm]["what"],
        "bar": BAR,
        "draws": DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "parts_read": folds_read(arm),
        "of_parts": FOLDS,
        "screen": (
            "a SCREEN and not the adoption bar: one part of the deal is fitted, so a positive "
            "result is informative and a null one is not. Read the motivating slice's "
            "positives and negatives before reading its interval"
        ),
        "baseline_is_in_sample": bool(ARMS.get(baseline, {}).get("artifact")),
        "rows": len(pairs),
        "lineages": len({row["lineage"] for _mine, row in pairs}),
        "motivating": motivating,
        "guards": guards,
        "clears_the_bar": (
            motivating["verdict"] == "better"
            and all(guard["verdict"] == "not worse" for guard in guards)
        ),
        "three_against_four": three_against_four(strange),
        "per_mode_ge4": per_mode(strange, 4),
        "per_mode_ge3": per_mode(strange, 3),
    }


def write_comparison(
    arm: str, baseline: str = "baseline", band_on: str | None = None
) -> tuple[Path, dict]:
    """The comparison as a record beside the arm it is about."""
    document = compare(arm, baseline, band_on)
    path = arm_dir(arm) / f"against_{baseline}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path, document


def standing(arm: str) -> dict:
    """One arm's own out-of-fold numbers, with a lineage interval on each.

    The absolute read beside the paired one: a delta says which arm is ahead, and
    this says what either of them can actually do.
    """
    import numpy

    rows = pooled(arm)
    out: dict = {"arm": arm, "rows": len(rows), "per_kind": {}}
    for kind in render_train.KINDS:
        members = [row for row in rows if row["kind"] == kind]
        lineages = numpy.array([row["lineage"] for row in members])
        cell: dict = {"n": len(members)}
        for cutpoint in (2, 3, 4):
            labels = numpy.array([int(row["score"]) >= cutpoint for row in members], dtype=float)
            scores = numpy.array([float(row[f"p_ge{cutpoint}"]) for row in members])
            interval = metrics.bootstrap(
                lambda picked, labels=labels, scores=scores: metrics.auc(
                    labels[picked], scores[picked]
                ),
                lineages,
                draws=DRAWS,
                seed=BOOTSTRAP_SEED,
            )
            cell[f"auc_ge{cutpoint}"] = {
                "value": metrics.auc(labels, scores),
                "positives": int(labels.sum()),
                "lo": interval["lo"],
                "hi": interval["hi"],
            }
        out["per_kind"][kind] = cell
    return out


__all__ = [
    "ARMS",
    "BAR",
    "BOOTSTRAP_SEED",
    "DRAWS",
    "FOLDS",
    "HOLDOUT_FOLD",
    "FOLD_SEED",
    "LAST_OVERRIDE",
    "MOTIVATING_BAND",
    "SCHEMA",
    "RULED_OUT",
    "SELECTION_OBJECTIVES",
    "SWEPT_BATCH",
    "CrossValidationError",
    "aligned",
    "arm_dir",
    "assignment",
    "assignment_path",
    "check_written_backbone",
    "compare",
    "declared_backbone",
    "fit",
    "fold_dir",
    "folds_read",
    "keyed",
    "out_of_fold_path",
    "per_mode",
    "pool",
    "pooled",
    "position_of",
    "read_assignment",
    "read_out_of_fold",
    "read_shipped",
    "root",
    "shipped_artifact",
    "sides_for",
    "standing",
    "swept",
    "top_cutpoint_loss",
    "three_against_four",
    "write_assignment",
    "write_comparison",
    "write_pooled",
]
