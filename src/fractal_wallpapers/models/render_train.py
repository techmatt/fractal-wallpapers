"""One render judge over both kinds: the candidate, trained and scored.

Two heads answer one question in two halves. `smooth_render` judges the smooth
coloring as a wallpaper; `strange_render` judges the seventeen others as
renderings. Both take a finished picture and return an ordinal verdict on the
same 1..4 scale, under recipes that differ in exactly one behavioural key — the
backbone. So the question this module exists to answer is whether the split is
load-bearing at all, or whether **one** head over the pooled stores would judge
each kind as well as its own head does. If it would, the system is simpler by one
head, one store boundary and one release artifact.

**Nothing here adopts anything.** The shipped heads, their floors, the acceptance
records and every wire in the supply and curation paths are untouched. This
trains a candidate into its own directory and scores it on the two blind sheets;
[`fractal_wallpapers.models.render_acceptance`] reads it against the bar. What
adoption would cost is written down in the report and done nowhere.

## The split rule is stricter than either incumbent faced

The two stores stamp their own evaluation sides, and they are disjoint: 197
locations pinned to `blind_minibrot`, 110 to `blind_modes`, no location in both.
A joint head has to keep **both** instruments clean, so its training side is the
intersection of the two training sides — a location pinned in *either* store is
out, whichever store the row came from.

That is stricter than what the incumbents trained under. Five locations pinned to
the strange sheet also carry smooth rows, and the smooth incumbent trained on
those 28 rows perfectly legitimately: they are not on its instrument. The
candidate does not get them. The direction is deliberate — every deviation from
the incumbents' conditions here costs the candidate rather than pays it, so a
non-inferiority verdict is not something the split bought.

## The picture is the input, and that is the whole design

No kind flag, no mode embedding, no conditioning of any sort. A head handed the
kind would be free to keep a scale per kind, which is two heads sharing a
backbone rather than one head — and the deliverable of a pooled head is one scale
over one population. What it sees is what the incumbents see: a picture.

## Everything else is the incumbents' recipe, and one key had to be chosen

The two recipes agree on every behavioural key but the backbone: medium for
smooth renders, small for strange. One head has one backbone, so this is the one
value that cannot be inherited and had to be picked. [`RECIPE`] takes the
**medium**, and the reason is capacity against corpus size: the pooled training
side is larger than either constituent, and medium is the backbone already proven
on the larger of the two. It is a pinned choice rather than a tuned one — nothing
here searches over it, and the report says so.

The sampler, the class balance, the augmentation, the epoch count and the
selection objective are carried unchanged, and the selection *slice* is drawn by
the same rule at the same share and the same seed, over the pooled training
side's places. The objective is a controlled variable: a candidate chosen under a
different rule from the incumbents would be measuring its own selection.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import storage
from fractal_wallpapers.labeling import finished, groups
from fractal_wallpapers.models import finished_train, head, metrics, renders, train
from fractal_wallpapers.paths import repo_root, tracked_name

#: The schema every record here carries.
SCHEMA = 1

#: THE head. One judge over both kinds, and the name a release carries it under.
HEAD = "render"

#: The two kinds it pools, in the order every table here reports them.
KINDS: tuple[str, ...] = ("smooth_render", "strange_render")

#: The third side, and the slice that carves it out. Carried from the incumbents
#: unchanged, because the selection population is a controlled variable.
SELECTION = finished_train.SELECTION
SELECTION_SHARE = finished_train.SELECTION_SHARE
SELECTION_SEED = finished_train.SELECTION_SEED

#: The side a row lands on when it is train-side in its own store and pinned in
#: the other. Counted and reported rather than quietly dropped: it is exactly
#: what the strict split rule costs.
EXCLUDED = "excluded"

#: The candidate's whole recipe. Every value is the incumbents' shared one except
#: `backbone`, which the two incumbents disagree about and which is pinned here to
#: the larger of the pair — see the module docstring.
RECIPE: dict = {
    **finished_train.COMMON,
    "classes": 4,
    "backbone": finished_train.RECIPES["smooth_render"]["backbone"],
    "selection_cutpoint": 3,
    "conditioning": "none — the picture is the input, and the head is told no kind",
}

#: Every band this study has registered a bar against, newest last. A candidate is
#: a whole design plus the runs that realize it; the bar is written per candidate
#: and before its band exists.
#:
#: `medium` was the first, and its FAIL is on the record. It traced to the one
#: value a joint head cannot inherit — the two incumbents disagree about the
#: backbone and one head has one — so `small_backbone` re-asks it at the strange
#: incumbent's, which is the corpus that was starving. Everything else about the
#: two is identical: shared classifier, no conditioning, pooled rows, the same
#: intersection split and the same frozen selection protocol.
#:
#: `enlarged_corpus` is the first candidate here that is not a design question at
#: all. Nothing about the recipe moves — same backbone, same shared classifier, same
#: frozen selection objective and population rule — and the only thing that changed
#: is that the two stores grew by the manufactured rare-colour batch. Which is why
#: it is the first candidate whose incumbent is not the pair of retired per-kind
#: heads but **the shipped joint head itself**: `incumbent` names it, and a
#: candidate that omits the key is gated against the per-kind pair as before.
CANDIDATES: dict[str, dict] = {
    "medium": {
        "runs": ("seed0", "seed1", "seed2"),
        "backbone": finished_train.RECIPES["smooth_render"]["backbone"],
        "what": (
            "the shared-classifier joint head at the smooth incumbent's backbone. The first "
            "registered candidate; its bar reads FAIL"
        ),
    },
    "small_backbone": {
        "runs": ("small_backbone_seed0", "small_backbone_seed1", "small_backbone_seed2"),
        "backbone": finished_train.RECIPES["strange_render"]["backbone"],
        "what": (
            "the same head at the STRANGE incumbent's backbone. The prior band's failure "
            "traced to capacity against the strange corpus rather than to pooling, and this "
            "is that one value re-asked"
        ),
    },
    "enlarged_corpus": {
        "runs": ("enlarged_corpus_seed0", "enlarged_corpus_seed1", "enlarged_corpus_seed2"),
        "backbone": finished_train.RECIPES["strange_render"]["backbone"],
        "incumbent": "small_backbone",
        "band_only": True,
        "what": (
            "the shipped design, unchanged, on the corpus after the manufactured "
            "rare-colour batch landed in both stores. No recipe key moves; the question is "
            "only whether growing the corpus costs anything on either blind sheet"
        ),
    },
}

#: The candidate a bare read is about. The newest registered one.
CURRENT = "enlarged_corpus"

#: The band of the first candidate, kept as a name because the historical arm and
#: several guards read it.
RUNS: tuple[str, ...] = CANDIDATES["medium"]["runs"]

#: The variants. Each is a candidate with ONE thing moved, trained into its own
#: runs, and every one is REPORTED rather than gated: a bar is written about one
#: design, and a bar a different design could satisfy is not a bar.
#:
#: `two_head` — one backbone, **two last layers**, one ordinal head per kind. It
#: needs no new module: a CORN head over `classes` tiers emits `classes - 1`
#: logits, and one `Linear` of twice that width IS two independent heads, because
#: the rows of a linear map do not interact and an example of one kind reaches
#: only its own kind's rows. See [`cutpoints_of`]. It is **conditioned** and the
#: candidates are not — it has to be told which kind it is reading, which costs
#: nothing here (the mode decides the kind) but is no longer "the picture is the
#: input".
#:
#: `two_head_small` is the same question at the backbone where the strange corpus
#: is not starving. At the medium backbone the split-classifier arm lost, but so
#: did everything else that shared less — sharing was standing in for data, and a
#: one-seed negative there could not tell the two apart.
VARIANTS: dict[str, dict] = {
    "two_head": {
        "runs": ("two_head_seed0",),
        "backbone": finished_train.RECIPES["smooth_render"]["backbone"],
        "against": "medium",
        "what": (
            "one backbone, two last layers — one ordinal head per kind, at the MEDIUM "
            "backbone. Shares every representation and lets the two kinds keep two scales, "
            "at the cost of having to be told which kind it is reading"
        ),
    },
    "two_head_small": {
        "runs": ("two_head_small_seed0", "two_head_small_seed1", "two_head_small_seed2"),
        "backbone": finished_train.RECIPES["strange_render"]["backbone"],
        "against": "small_backbone",
        "what": (
            "the same two last layers at the SMALL backbone, three seeds — the read the "
            "medium one could not give, because there sharing was standing in for data"
        ),
    },
}

#: Kept as a name because the guard that says the variants may not gate reads it.
TWO_HEAD_RUNS: tuple[str, ...] = VARIANTS["two_head"]["runs"]

#: Every run of every variant, which is what a comparison has to align over.
VARIANT_RUNS: tuple[str, ...] = tuple(run for entry in VARIANTS.values() for run in entry["runs"])

#: Runs that are on disk and belong to no band, with what happened to them.
#:
#: A band is a design plus the runs that realize it, so a run that did not train
#: the design cannot stay in the band — its records would be read against a bar
#: written about something else. It is not deleted either: it trained, it cost
#: hours, and what it says about the design it *did* train is worth keeping.
#: So it is renamed out of the band and named here.
#:
#: These three are the whole of it. `enlarged_corpus` declares the small
#: backbone, its bar states the recipe as "the incumbent's, unchanged in every
#: key including the backbone", and all three runs trained at the **medium** —
#: [`RECIPE`]'s pinned default, taken because nothing read the declaration and
#: the launches passed no `--backbone`. Their records are internally consistent
#: and consistently wrong, which is why the checkpoint being 3.3x the expected
#: size is what gave it away. [`check_declared_backbone`] is what stops it
#: happening at launch and [`check_written_backbone`] is what sees it afterwards.
MISLAUNCHED: dict[str, dict] = {
    "mislaunch_medium_seed0": {"launched_as": "enlarged_corpus_seed0"},
    "mislaunch_medium_seed1": {"launched_as": "enlarged_corpus_seed1"},
    "mislaunch_medium_seed2": {"launched_as": "enlarged_corpus_seed2"},
}

#: What the runs above were, in one sentence, carried onto anything that reports
#: them. They answer no bar and gate nothing.
MISLAUNCH_BASIS = (
    "launched 2026-08-24 without --backbone, so all three took RECIPE's pinned medium "
    "rather than the small backbone the enlarged_corpus band and its bar declare. Renamed "
    "out of that band on 2026-08-24: they realize no registered design and answer no bar"
)

#: Every band with a bar, candidates and variants alike, keyed by run name. A
#: band **declares** its recipe and its runs together, and this is the index that
#: lets a run name answer which declaration it is supposed to realize.
DECLARED_BY_RUN: dict[str, tuple[str, dict]] = {
    run: (name, entry)
    for source in (CANDIDATES, VARIANTS)
    for name, entry in source.items()
    for run in entry["runs"]
}


def declared_for(run_name: str | None) -> tuple[str, dict] | None:
    """`(band, entry)` for a named run, or `None` for a run no band declares.

    A run outside every band is a scratch run and stays free: nothing has written
    a bar about it, so there is no declaration for it to disagree with.
    """
    if not run_name:
        return None
    return DECLARED_BY_RUN.get(str(run_name))


def declared_backbone(run_name: str | None) -> str | None:
    """The backbone the band this run belongs to says it is trained at."""
    found = declared_for(run_name)
    return None if found is None else str(found[1]["backbone"])


def check_declared_backbone(run_name: str, recipe: dict) -> None:
    """Refuse a recipe whose backbone is not the one this run's band declares.

    **The declaration is the bar.** `bar_enlarged_corpus.json` states the recipe
    as "the incumbent's, unchanged in every key including the backbone
    (mobilenetv4_conv_small…)", and [`CANDIDATES`] says the same thing in code —
    but for as long as neither was *read* at launch, the value that actually
    trained was [`RECIPE`]'s, which is the first candidate's medium. All three
    `enlarged_corpus` runs of 2026-08-24 were launched that way and trained at
    the medium backbone: a band that did not realize the design its own bar was
    written about, read as though it did, and only a 3.3x checkpoint size gave it
    away.

    Nothing about that was detectable from the record — `config.json` agreed with
    the checkpoint, the audit agreed with both, and every one of them agreed on
    the wrong value. So the declaration is enforced in the two places it can be:
    here, before a launch spends hours, and in
    [`fractal_wallpapers.models.render_acceptance`], before a written band is
    read against a bar it may not answer.
    """
    declared = declared_backbone(run_name)
    if declared is None:
        return
    band, _ = declared_for(run_name)
    actual = str(recipe.get("backbone"))
    if actual != declared:
        raise TrainingError(
            f"run {run_name!r} belongs to the {band!r} band, which declares the backbone "
            f"{declared!r}, and this launch would train at {actual!r}. The bar for that band "
            f"was written about the declared design and a band trained at another backbone "
            f"cannot answer it. Drop --backbone to take the declared value, or train under a "
            f"run name no band claims."
        )


def written_backbone(run_name: str) -> str | None:
    """What a run's tracked `config.json` says it actually trained at.

    `None` where the run has no record here — a band read against runs that were
    never written is a different refusal, and it belongs to the reader.
    """
    import json as _json

    path = config_path(run_name)
    if not path.is_file():
        return None
    return str(_json.loads(path.read_text(encoding="utf-8")).get("backbone"))


def check_written_backbone(run_names) -> None:
    """Refuse a band whose written runs did not train at the declared backbone.

    The launch-time check above stops this happening again; this one is what sees
    it when it already has. A run records the recipe it ran, so `config.json`,
    the checkpoint's own config and `head audit` all agree — with each other, and
    with the wrong value. Nothing in a run directory can tell you the band was
    supposed to be something else, because the only place that says so is the
    declaration.
    """
    wrong = []
    for run_name in run_names:
        declared = declared_backbone(run_name)
        written = written_backbone(run_name)
        if declared is not None and written is not None and written != declared:
            band, _ = declared_for(run_name)
            wrong.append((run_name, band, declared, written))
    if not wrong:
        return
    lines = "; ".join(
        f"{run_name} ({band} declares {declared}, the run trained at {written})"
        for run_name, band, declared, written in wrong
    )
    raise TrainingError(
        f"{len(wrong)} run(s) of this band did not train at the backbone their band declares, "
        f"so the band does not realize the design its bar was written about: {lines}. "
        f"Re-train them under the declared recipe, or record them as a mis-launch under run "
        f"names no band claims — a read of these against that bar reads one design against a "
        f"bar for another."
    )


#: What the candidate inherited, and every key that could not come across.
INHERITANCE = {
    "identical_to_both_incumbents": [
        "amp",
        "augmentation",
        "backbone_lr",
        "batch_size",
        "border_crop",
        "class_balance",
        "classes",
        "drop_path_rate",
        "drop_rate",
        "epochs",
        "geometry",
        "grad_clip",
        "head_lr",
        "loss",
        "pretrained",
        "sampler",
        "selection",
        "selection_cutpoint",
        "source_dims",
        "target_dims",
        "weight_decay",
    ],
    "chosen": [
        {
            "key": "backbone",
            "was": "medium for smooth renders, small for strange — the one behavioural key "
            "the two incumbent recipes disagree about",
            "now": "the medium, for both",
            "why": "one head has one backbone, so this value cannot be inherited and had to "
            "be picked. Capacity is chosen against corpus size and the pooled training side "
            "is larger than either constituent, so the backbone already proven on the larger "
            "of the two is the one that carries over. PINNED, not tuned: nothing here "
            "searches over it, and a candidate that failed at this backbone is not evidence "
            "about the other.",
        },
        {
            "key": "split",
            "was": "each store's own eval-only pin, and nothing else",
            "now": "the INTERSECTION of the two training sides — a location pinned in either "
            "store is out of training, whichever store the row came from",
            "why": "a joint head is read on both blind sheets, so both instruments have to "
            "stay clean. It is stricter than what either incumbent faced and it costs the "
            "candidate rows the smooth incumbent legitimately trained on. Conservative "
            "against the candidate, on purpose.",
        },
        {
            "key": "selection_population",
            "was": "a seeded 10% slice of each head's own training side, drawn over places",
            "now": "the same rule at the same share and seed, over the POOLED training "
            "side's places",
            "why": "the objective and the drawing rule are controlled variables; the "
            "population follows the head. A place carrying both kinds sits whole on one "
            "side, so no location straddles the boundary in either kind.",
        },
    ],
}


class TrainingError(RuntimeError):
    """A judge that cannot be trained or scored on what is here."""


def head_dir(run: str | None = None) -> Path:
    """Where the candidate lives. **Beside** the shipped heads, never inside one.

    Not on [`fractal_wallpapers.models.roster.HEADS`], so no release carries it
    and `fetch-weights` never asks for it; `.pt` files under `models/` are
    ignored by the same rule that ignores every other head's, so the weights stay
    out of history while the records that describe them do not.
    """
    base = repo_root() / "models" / HEAD
    return base / run if run else base


def checkpoint_path(which: str = "best", run: str | None = None) -> Path:
    return head_dir(run) / f"{which}.pt"


def config_path(run: str | None = None) -> Path:
    return head_dir(run) / "config.json"


def metrics_path(run: str | None = None) -> Path:
    return head_dir(run) / "metrics.json"


def scores_path(kind: str, run: str | None = None) -> Path:
    """One kind's blind sheet, read through the candidate. One file per kind."""
    return head_dir(run) / f"scores_{finished.head_of(kind)}.jsonl"


@dataclass
class Picture(finished_train.Picture):
    """One pooled training unit. The incumbents' unit, plus which store it is from.

    `kind` is recorded and reported and is **never** handed to the model — see
    the module docstring. It exists so a read can be cut per kind afterwards.
    """

    kind: str = ""


def pinned_everywhere() -> dict[tuple, str]:
    """`{location: the store that pinned it}` over both stores.

    The union, because the split rule is an intersection of training sides: a
    location on either instrument is out of the candidate's training.
    """
    out: dict[tuple, str] = {}
    for kind in KINDS:
        for place in finished.pinned(kind):
            out.setdefault(place, kind)
    return out


def population(only: str | None = None) -> tuple[list[Picture], dict]:
    """Every judged picture of both stores, on the side the strict rule puts it.

    Four sides rather than three. A row whose place is pinned in **its own**
    store is that sheet's evaluation row; a row whose place is pinned only in the
    **other** store is [`EXCLUDED`] — it may not train, because that would spend
    the other head's instrument, and it is not on any sheet this candidate is
    read against. Everything else trains, and the selection slice is drawn out of
    it afterwards over places.
    """
    import random

    forbidden = pinned_everywhere()
    pictures: list[Picture] = []
    absent: list[str] = []
    per_kind: dict[str, dict] = {}
    for kind in KINDS:
        own = set(finished.pinned(kind))
        rows = finished.resolved(kind).scored()
        crops = renders.crop_dir(kind)
        counted = {"rows": len(rows), "eval": 0, EXCLUDED: 0, "train_side": 0}
        for row in rows:
            name = renders.job_name({**row, "_head": kind})
            path = crops / f"{name}.jpg"
            if not path.is_file():
                absent.append(name)
                continue
            place = finished.place_of(row)
            if place in own:
                side = "eval"
            elif place in forbidden:
                side = EXCLUDED
            else:
                side = "train"
            counted["train_side" if side == "train" else side] += 1
            pictures.append(
                Picture(
                    path=path,
                    score=int(row["score"]),
                    side=side,
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
        raise TrainingError(
            f"{len(absent)} judged pictures are not in a render cache (e.g. {absent[:3]}). "
            f"Build both before training: a head trained on the subset that happened to be "
            f"on disk is a head nobody can reproduce."
        )

    beyond = sorted({picture.score for picture in pictures if picture.score > RECIPE["classes"]})
    if beyond:
        raise TrainingError(
            f"the pooled corpus holds verdicts at tier(s) {beyond} and this recipe trains "
            f"{RECIPE['classes']} classes."
        )

    training = [picture for picture in pictures if picture.side == "train"]
    places = sorted({picture.place for picture in training})
    draw = random.Random(SELECTION_SEED)
    draw.shuffle(places)
    chosen = set(places[: max(1, round(len(places) * SELECTION_SHARE))])
    for picture in training:
        if picture.place in chosen:
            picture.side = SELECTION

    # The ablation, and it is a filter applied AFTER every side is decided rather
    # than a population drawn on its own. That ordering is the whole point: the
    # ablation's training side is exactly the pooled one intersected with a kind,
    # and its selection slice is exactly the pooled slice intersected with the
    # same kind. Drawing a slice over one kind's own places would move two things
    # at once and the arm would answer nothing.
    if only is not None:
        only = finished.head_of(only)
        pictures = [picture for picture in pictures if picture.kind == only]

    record = {
        "only": only,
        "rule": (
            "the intersection of the two training sides: a location pinned in either store "
            "may not train, whichever store its row came from"
        ),
        "pinned_locations": {kind: len(finished.pinned(kind)) for kind in KINDS},
        "pinned_locations_union": len(forbidden),
        "per_kind": per_kind,
        "excluded_pictures": sum(1 for p in pictures if p.side == EXCLUDED),
        "excluded_locations": len({p.place for p in pictures if p.side == EXCLUDED}),
        "selection": {
            "share": SELECTION_SHARE,
            "seed": SELECTION_SEED,
            "drawn_over": "places on the pooled training side, so a place cannot straddle",
            "places": len(chosen),
            "of_places": len(places),
            "pictures": sum(1 for p in pictures if p.side == SELECTION),
        },
    }
    return pictures, record


def sides(pictures: list[Picture]) -> dict[str, list[Picture]]:
    out: dict[str, list[Picture]] = {"train": [], SELECTION: [], "eval": [], EXCLUDED: []}
    for picture in pictures:
        out[picture.side].append(picture)
    return out


def of_kind(pictures: list[Picture], kind: str) -> list[Picture]:
    return [picture for picture in pictures if picture.kind == kind]


def cluster_of(rows: list[dict]) -> list[int]:
    """Bootstrap clusters over score rows: the neighbourhood group of each row.

    The exact non-`c` axes, through [`fractal_wallpapers.labeling.groups`] — the
    same rule the location split is drawn over. Frames a hair apart on one plane
    are the same picture twice, and resampling them as independent evidence
    reports an interval two to three times too narrow.
    """
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise TrainingError(
            f"{grouping.n_unplaced} score rows carry no location identity, so they cannot be "
            f"grouped. A paired interval over rows that were not clustered is a decoration."
        )
    return [int(group) for group in grouping.of_row]


def classifier_width(classes: int, per_kind: bool) -> int:
    """What to ask [`head.build`] for. It takes tiers and emits tiers minus one.

    One head wants `classes`. Two want a classifier `len(KINDS)` times as wide,
    which is `1 + (classes - 1) * len(KINDS)` tiers in that function's currency.
    """
    return 1 + (classes - 1) * (len(KINDS) if per_kind else 1)


def cutpoints_of(logits, kinds, classes: int, per_kind: bool):
    """The cutpoint logits each row's own kind owns.

    A no-op for the single head, which has one set and gives it to everybody.
    For the two-headed variant it is a gather: reshape the wide classifier into
    `(row, kind, cutpoint)` and take each row's own kind's slice. Nothing is
    masked and nothing is zeroed — the rows a kind does not own are simply never
    read, so they never appear in a loss and never receive a gradient.
    """
    if not per_kind:
        return logits
    import torch

    width = classes - 1
    reshaped = logits.view(logits.shape[0], len(KINDS), width)
    return reshaped[torch.arange(logits.shape[0], device=logits.device), kinds]


class KindCrops(finished_train.Crops):
    """The candidate's training set, plus which kind each example is.

    Defined at module level for the reason its parent is — a loader worker on
    Windows is spawned and re-imports the dataset by name, and a class with no
    importable name kills the child.
    """

    def __getitem__(self, index: int):
        crop, score, position = super().__getitem__(index)
        return crop, score, KINDS.index(self.rows[index].kind), position


def _loader(pictures: list[Picture], transform, recipe: dict, where: str, per_kind: bool = False):
    """The incumbents' loader, over the pooled rows. Sampler and weights are theirs."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    examples = (KindCrops if per_kind else finished_train.Crops)(pictures, transform)
    raw, mass = finished_train.weights(pictures)
    sampler = WeightedRandomSampler(
        torch.tensor(raw, dtype=torch.double), num_samples=len(pictures), replacement=True
    )
    loader = DataLoader(
        examples,
        batch_size=recipe["batch_size"],
        sampler=sampler,
        num_workers=recipe["workers"],
        pin_memory=(where == "cuda"),
        persistent_workers=False,
        drop_last=False,
    )
    return examples, loader, mass


def score_through(model, paths, kinds, transform, where: str, classes: int, recipe: dict):
    """Every picture through the deploy transform, read at its own kind's cutpoints.

    [`train.score`] with the gather folded in. It is spelled here rather than
    passed a flag because the single-head path must keep reaching the shared
    function untouched: those three seeds are trained and their numbers are on
    the record.
    """
    import numpy
    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset

    class Pictures(Dataset):
        def __len__(self) -> int:
            return len(paths)

        def __getitem__(self, index: int):
            with Image.open(paths[index]) as opened:
                opened.load()
                image = opened.convert("RGB")
            return transform(image), KINDS.index(kinds[index]), index

    model.eval()
    out = numpy.zeros((len(paths), classes - 1), dtype=numpy.float64)
    loader = DataLoader(
        Pictures(),
        batch_size=recipe["batch_size"],
        shuffle=False,
        num_workers=0,
        pin_memory=(where == "cuda"),
    )
    with torch.no_grad():
        for pictures, kind, index in loader:
            logits = model(pictures.to(where, non_blocking=True))
            mine = cutpoints_of(logits, kind.to(logits.device), classes, per_kind=True)
            out[index.numpy()] = mine.float().cpu().numpy()
    return head.probabilities(out)


def load_checkpoint(path, device: str = "auto"):
    """Rebuild the judge from a checkpoint FILE. What `ship` and the servers use.

    Same rule as [`load`] and for the same reason — the classifier width comes off
    the config's `per_kind`, not off `classes` — but addressed by path, because a
    shipped artifact does not live in a run directory.
    """
    import torch

    where = train.device_of(device)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    model = head.build(
        num_classes=classifier_width(int(config["classes"]), bool(config.get("per_kind"))),
        backbone=config["backbone"],
        pretrained=False,
    )
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


def load(which: str = "best", run_name: str | None = None, device: str = "auto"):
    """Rebuild a candidate from its checkpoint. The config in the file decides how.

    Not [`fractal_wallpapers.models.finished_scoring.load`], because that one
    builds a classifier as wide as `classes` says and the two-headed variant's is
    wider. The config carries `per_kind` and that is what decides.
    """
    import torch

    where = train.device_of(device)
    saved = torch.load(checkpoint_path(which, run_name), map_location="cpu", weights_only=False)
    config = saved["config"]
    model = head.build(
        num_classes=classifier_width(int(config["classes"]), bool(config.get("per_kind"))),
        backbone=config["backbone"],
        pretrained=False,
    )
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


def run(
    device: str = "auto",
    epochs: int | None = None,
    seed: int | None = None,
    run_name: str | None = None,
    only: str | None = None,
    per_kind: bool = False,
    backbone: str | None = None,
    split=None,
    directory: Path | None = None,
    target_dims=None,
    selection=None,
    selection_says: str | None = None,
    log=train.say,
) -> dict:
    """Train the candidate at one seed, and write its checkpoints and records.

    `only` trains the **ablation** rather than the candidate: one kind's share of
    exactly the pooled split, under exactly this recipe. It is the arm that says
    whether a difference between the candidate and an incumbent is about pooling
    or about one of the two things pooling changed along with it — the corpus the
    smooth incumbent trained on has grown since, and the strange incumbent's
    backbone is not this one.

    **`split` and `directory` are how a caller re-uses this loop over a different
    partition of the same corpus, and they exist for one caller.**
    [`fractal_wallpapers.models.render_cv`] fits this recipe on cross-validation
    folds — the same recipe over a different split, which must not become a
    second implementation of it, because a baseline that is a re-typed trainer
    measures the re-typing. `split` is called instead of [`population`] and
    returns what it returns; `directory` is where the checkpoints and records
    land, so a fold does not claim a run directory beside the shipped bands.
    Both default to what every band on the record was trained under, and the
    recipe, the loop, the selection objective and the records are untouched by
    either.

    **`selection` moves the one thing an arm may want to move about how the epoch
    is chosen**, and `selection_says` is the sentence that goes into the written
    recipe beside it — an unlabelled objective would leave two runs whose configs
    agree and whose epochs were chosen by different rules. It takes
    `(labels, probabilities, classes)` and returns a number to MINIMIZE, which is
    what [`finished_train.validation_loss`] is and what the default stays.

    **`target_dims` moves the input size**, which the recipe has always carried
    as a record of what the head reads at and which is now read as well as
    written. `None` keeps the value every band on the record trained under.
    """
    import numpy
    import torch

    for kind in KINDS:
        storage.require_hot(renders.cache_dir(kind), what="training the joint render candidate")
    recipe = dict(RECIPE)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if seed is not None:
        recipe["seed"] = int(seed)
    # The band's DECLARED backbone, not the module's default. `RECIPE` carries
    # the first candidate's medium, and every band since has re-asked that one
    # value in its own declaration — so a named run takes its band's value and a
    # `--backbone` that disagrees with it is refused rather than obeyed.
    declared = declared_backbone(run_name)
    if declared is not None:
        recipe["backbone"] = declared
    if backbone is not None:
        recipe["backbone"] = backbone
    if run_name:
        check_declared_backbone(run_name, recipe)
    if target_dims is not None:
        recipe["target_dims"] = [int(value) for value in target_dims]
    if selection_says is not None:
        recipe["selection"] = selection_says
    if per_kind:
        recipe["per_kind"] = True
        recipe["conditioning"] = (
            "the LAST LAYER ONLY — one ordinal head per kind over a shared backbone. The "
            "head has to be told which kind it is reading, which the single head does not"
        )
    classes = int(recipe["classes"])

    where = train.device_of(device)
    train.set_seed(int(recipe["seed"]))
    pictures, split_record = split() if split is not None else population(only)
    by_side = sides(pictures)
    training, choosing = by_side["train"], by_side[SELECTION]
    holdout, dropped = by_side["eval"], by_side[EXCLUDED]
    if not choosing:
        raise TrainingError("the selection slice is empty; there is nothing to choose an epoch on")

    # The check run on the split that was BUILT, over BOTH pins: a pass that
    # never consulted either one still dies here.
    forbidden = {repr(place) for place in pinned_everywhere()}
    trespassing = [p for p in training + choosing if p.place in forbidden]
    if trespassing:
        raise TrainingError(
            f"{len(trespassing)} training pictures sit on a location pinned to one of the two "
            f"evaluation sheets (e.g. batch {trespassing[0].batch!r}). Both instruments have "
            f"to stay clean for this comparison — fix the split, never the pin."
        )

    log(
        f"device {where}  torch {torch.__version__}  seed {recipe['seed']}  "
        f"run {run_name}  only {only}"
    )
    log(
        f"pictures {len(pictures)}: train {len(training)} {finished_train.histogram(training)}, "
        f"selection {len(choosing)} {finished_train.histogram(choosing)}, "
        f"eval {len(holdout)}, excluded by the strict split {len(dropped)}"
    )
    for kind in KINDS:
        log(
            f"  {kind}: train {len(of_kind(training, kind))} "
            f"selection {len(of_kind(choosing, kind))} eval {len(of_kind(holdout, kind))} "
            f"excluded {len(of_kind(dropped, kind))}"
        )

    width = classifier_width(classes, per_kind)
    probe = head.build(
        num_classes=width, backbone=recipe["backbone"], pretrained=recipe["pretrained"]
    )
    data_config = head.data_config(probe)
    del probe
    log(f"data config {data_config}")

    model = head.build(
        num_classes=width,
        backbone=recipe["backbone"],
        pretrained=recipe["pretrained"],
        drop_rate=recipe["drop_rate"],
        drop_path_rate=recipe["drop_path_rate"],
    ).to(where)
    head_parameters = list(model.get_classifier().parameters())
    head_ids = {id(parameter) for parameter in head_parameters}
    backbone_parameters = [p for p in model.parameters() if id(p) not in head_ids]
    optimizer = torch.optim.AdamW(
        [
            {"params": backbone_parameters, "lr": recipe["backbone_lr"]},
            {"params": head_parameters, "lr": recipe["head_lr"]},
        ],
        weight_decay=recipe["weight_decay"],
    )
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=recipe["epochs"])

    # Geometric only. The coloring is the label for both kinds, so the colour
    # stages are off here exactly as they are off in both incumbent recipes.
    # `target_dims` has always been in the recipe as a record of what the head
    # reads at; here it is read rather than only written, so an arm may ask
    # whether the answer is in the detail that size discards. Every band on the
    # record carries the shipped value and is unmoved by this.
    target = tuple(recipe["target_dims"])
    train_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=True,
        border_crop=recipe["border_crop"],
        jpeg=None,
        brightness=0.0,
        contrast=0.0,
        target=target,
    )
    deploy_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=False,
        target=target,
    )
    examples, loader, mass = _loader(training, train_transform, recipe, where, per_kind)
    log(f"sampled mass {json.dumps(mass['sampled_mass'])} over {mass['places']} places")

    choosing_paths = [picture.path for picture in choosing]
    choosing_labels = numpy.array([picture.score for picture in choosing])
    choosing_kinds = numpy.array([picture.kind for picture in choosing])
    cutpoint = min(int(recipe["selection_cutpoint"]), classes) - 2

    directory = directory or head_dir(run_name)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        lock = train.claim(directory)
    except RuntimeError as taken:
        raise TrainingError(str(taken)) from None
    resume = directory / "resume.pt"

    best_metric, best_state, best_epoch, history = float("inf"), None, -1, []
    segments, start = [], 0
    if resume.is_file():
        saved = torch.load(resume, map_location="cpu", weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        schedule.load_state_dict(saved["schedule"])
        best_metric, best_epoch = saved["best_metric"], saved["best_epoch"]
        best_state, history = saved["best_state"], saved["history"]
        segments = list(saved.get("segments") or [])
        start = saved["epoch"] + 1
        torch.set_rng_state(saved["torch_rng"].cpu().to(torch.uint8))
        if where == "cuda" and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(
                [state.cpu().to(torch.uint8) for state in saved["cuda_rng"]]
            )
        numpy.random.set_state(saved["numpy_rng"])
        log(f"resumed at epoch {start} (best {best_metric:.4f} at epoch {best_epoch})")

    began = time.time()

    def launched(through: int) -> list[dict]:
        if through < start:
            return list(segments)
        return [
            *segments,
            {
                "from_epoch": start,
                "through_epoch": through,
                "wall_seconds": round(time.time() - began, 1),
            },
        ]

    for epoch in range(start, recipe["epochs"]):
        examples.set_epoch(epoch)
        model.train()
        clock, running, seen = time.time(), 0.0, 0
        for batch in loader:
            crops, labels = batch[0].to(where, non_blocking=True), batch[1].to(where)
            kinds = batch[2].to(where) if per_kind else None
            optimizer.zero_grad(set_to_none=True)
            logits = cutpoints_of(model(crops), kinds, classes, per_kind)
            loss = head.loss_of(logits, labels, num_classes=classes)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), recipe["grad_clip"])
            optimizer.step()
            running += loss.item() * crops.size(0)
            seen += crops.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise TrainingError(f"the head went non-finite at epoch {epoch}")

        probabilities = (
            score_through(
                model, choosing_paths, choosing_kinds, deploy_transform, where, classes, recipe
            )
            if per_kind
            else train.score(model, choosing_paths, deploy_transform, where, classes, recipe)
        )
        objective = (selection or finished_train.validation_loss)(
            choosing_labels, probabilities, classes
        )
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "selection_loss": objective,
            f"selection_ap_ge{cutpoint + 2}": metrics.average_precision(
                (choosing_labels >= cutpoint + 2).astype(int), probabilities[:, cutpoint]
            ),
        }
        for index in range(classes - 1):
            record[f"selection_auc_ge{index + 2}"] = metrics.auc(
                (choosing_labels >= index + 2).astype(int), probabilities[:, index]
            )
            record[f"selection_mean_p_ge{index + 2}"] = float(probabilities[:, index].mean())
        # Reported per kind, never selected on: the epoch is chosen by the pooled
        # objective, which is what a pooled head's selection has to be.
        for kind in KINDS:
            mask = choosing_kinds == kind
            if mask.any():
                record[f"selection_loss_{kind}"] = finished_train.validation_loss(
                    choosing_labels[mask], probabilities[mask], classes
                )
        history.append(record)
        log(
            f"epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"val {train.shown(objective)}  "
            + "  ".join(
                f"{kind.split('_')[0]} {train.shown(record.get(f'selection_loss_{kind}'))}"
                for kind in KINDS
            )
            + "  "
            + "  ".join(
                f"AUC>={index + 2} {train.shown(record[f'selection_auc_ge{index + 2}'])}"
                for index in range(classes - 1)
            )
            + f"  ({record['seconds']}s)"
        )

        if objective is not None and objective < best_metric:
            best_metric, best_epoch = objective, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        temporary = directory / "resume.pt.partial"
        torch.save(
            {
                "epoch": epoch,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "schedule": schedule.state_dict(),
                "best_metric": best_metric,
                "best_epoch": best_epoch,
                "best_state": best_state,
                "history": history,
                "segments": launched(epoch),
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if where == "cuda" else None,
                "numpy_rng": numpy.random.get_state(),
            },
            temporary,
        )
        temporary.replace(resume)

    lock.unlink(missing_ok=True)
    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name,
        "only": only,
        "classifier_width": width,
        **recipe,
        "kinds": [only] if only else list(KINDS),
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "best_epoch": best_epoch,
        "inherited": INHERITANCE,
        "renders": {"seed": renders.SEED, "jpeg_quality": 90},
        "split": split_record,
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, directory / "best.pt")
    torch.save({"state_dict": last_state, "config": config}, directory / "last.pt")
    if resume.is_file():
        resume.unlink()

    record = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name,
        "only": only,
        "two_head": per_kind,
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "segments": launched(recipe["epochs"] - 1),
        "best_epoch": best_epoch,
        "best_selection_objective": best_metric,
        "selection_metric": "validation loss (minimized), pooled over both kinds",
        "pictures": {
            "total": len(pictures),
            "train": len(training),
            "selection": len(choosing),
            "eval": len(holdout),
            EXCLUDED: len(dropped),
        },
        "per_kind": {
            kind: {
                "train": len(of_kind(training, kind)),
                "selection": len(of_kind(choosing, kind)),
                "eval": len(of_kind(holdout, kind)),
                EXCLUDED: len(of_kind(dropped, kind)),
            }
            for kind in KINDS
        },
        "class_counts": {
            "train": finished_train.histogram(training),
            "selection": finished_train.histogram(choosing),
            "eval": finished_train.histogram(holdout),
        },
        "split": split_record,
        "sampled_mass": mass,
        "history": history,
        "checkpoints": {
            "best": tracked_name(directory / "best.pt"),
            "last": tracked_name(directory / "last.pt"),
        },
    }
    (directory / "config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (directory / "metrics.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def score(
    kind: str,
    which: str = "best",
    device: str = "auto",
    run_name: str | None = None,
    log=train.say,
) -> dict:
    """Read one kind's blind sheet through the candidate, and write the rows.

    The rows are the shape [`fractal_wallpapers.models.finished_scoring`] writes,
    so an incumbent's read and the candidate's read of one sheet line up field
    for field and a comparison never has to translate between two spellings.
    """
    import numpy

    kind = finished.head_of(kind)
    checkpoint = checkpoint_path(which, run_name)
    model, config, where = load(which, run_name, device)
    per_kind = bool(config.get("per_kind"))
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )

    own = set(finished.pinned(kind))
    rows = [row for row in finished.resolved(kind).scored() if finished.place_of(row) in own]
    if not rows:
        raise TrainingError(f"the {kind} store pins no location, so there is no sheet to read")

    names = [renders.job_name({**row, "_head": kind}) for row in rows]
    crops = renders.crop_dir(kind)
    paths = [crops / f"{name}.jpg" for name in names]
    absent = [name for name, path in zip(names, paths, strict=True) if not path.is_file()]
    if absent:
        raise TrainingError(
            f"{len(absent)} pictures of the {kind} sheet are not in the render cache "
            f"(e.g. {absent[:3]}). Build it before scoring."
        )
    log(f"scoring {len(rows)} pictures of the {kind} sheet through {checkpoint}")

    classes = int(config["classes"])
    probabilities = (
        score_through(model, paths, [kind] * len(paths), transform, where, classes, config)
        if per_kind
        else train.score(model, paths, transform, where, classes, config)
    )

    path = scores_path(kind, run_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row, name, probability in zip(rows, names, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "head": HEAD,
                "kind": kind,
                "run": run_name,
                "two_head": per_kind,
                "checkpoint": which,
                "name": name,
                "batch": row["batch"],
                "score": row["score"],
                "side": "eval",
                "partition": row.get("partition"),
                "family": row["family"],
                "viewport": row["viewport"],
                "mode": row["mode"],
                "mode_params": row.get("mode_params") or {},
                "curve": row["curve"],
                "colormap": row["colormap"],
                "recipe": row["recipe"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            record["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "head": HEAD,
        "kind": kind,
        "run": run_name,
        "checkpoint": str(checkpoint),
        "which": which,
        "pictures": len(rows),
        "wrote": str(path),
    }


def read(kind: str, run: str | None = None, path: Path | None = None) -> list[dict]:
    """One run's read of one sheet, schema-checked."""
    path = scores_path(kind, run) if path is None else Path(path)
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise TrainingError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


__all__ = [
    "EXCLUDED",
    "HEAD",
    "INHERITANCE",
    "KINDS",
    "MISLAUNCHED",
    "MISLAUNCH_BASIS",
    "RECIPE",
    "RUNS",
    "SCHEMA",
    "SELECTION",
    "SELECTION_SEED",
    "SELECTION_SHARE",
    "CANDIDATES",
    "CURRENT",
    "DECLARED_BY_RUN",
    "TWO_HEAD_RUNS",
    "VARIANTS",
    "VARIANT_RUNS",
    "TrainingError",
    "Picture",
    "KindCrops",
    "check_declared_backbone",
    "check_written_backbone",
    "checkpoint_path",
    "classifier_width",
    "cluster_of",
    "cutpoints_of",
    "config_path",
    "declared_backbone",
    "declared_for",
    "head_dir",
    "metrics_path",
    "load",
    "load_checkpoint",
    "of_kind",
    "pinned_everywhere",
    "population",
    "read",
    "run",
    "score",
    "score_through",
    "scores_path",
    "sides",
    "written_backbone",
]
