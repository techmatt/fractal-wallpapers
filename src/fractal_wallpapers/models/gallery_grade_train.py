"""The fine-tier head: an order inside the render judge's own top, and how it is fitted.

## What this head is, and what it is not

The shipped render judge answers *is this picture worth keeping*. It answers it
well and at the good end of its own scale it saturates: over the `gallery_grade`
store's thousand rows the judge's `P(>=4)` correlates with a person's grade at
Spearman **+0.171**, and of the 237 rows it puts at `P(>=4) >= 0.99` one is a 1,
twenty-six are 2s and a hundred and nine are 3s. So a seating that walks the
judge's order and takes the first `n` is taking an order nobody fitted to the
question it is being asked.

This head is fitted to that question. It is the **second stage of a cascade
behind `p_ge4`** and never a standalone scalar: its output is undefined on a row
that never cleared the gate, because every row it was fitted on had cleared one.
A pool-wide ranking read off it would be a ranking over a population it has never
seen, and no reading here may be quoted as one.

## A separate network, initialised from the shipped judge

Same architecture as the render judge — [`head.build`] on the small backbone, the
four-tier CORN ordinal classifier — and the weights start at
`models/render/render.fp16.pt`, the shipped **weights-v6** artifact.

**Never a shared trunk.** A trunk this fit moved would be a judge flip: the pool's
`p_ge4` column would move under it, which empties the seating pool and forces a
full rescore. The initialisation is a copy and the two nets are strangers
afterwards.

## The 640 column, and what it costs

A grade was cast on the sheet's 1280x720 ss2 picture; this fits on the ledger's
stored **640x360** candidate, which is the column a mining pass and a seating
actually read. The two geometries are not resamplings of each other and they
disagree: over the landed thousand they correlate at r = 0.696, with **55** rows
reading `P(>=4) < 0.5` at label geometry against none at candidate geometry.

Fitting on the 640 column therefore accepts a **label-quality cost** — some rows
carry a verdict about a picture a little different from the one the head is shown
— and it is accepted deliberately, because that is where the head serves. The
alternative buys a cleaner fit for a head read at a geometry nothing seats at.

## The recipe is the shipped judge's, unchanged

Every behavioural key is read out of `render.fp16.pt`'s own committed config and
carried: twenty epochs, patience six, batches of thirty-two, the two learning
rates, the decay, the drop rates, the gradient clip, geometric augmentation only,
the sqrt class balance times the per-place weight, and the epoch chosen on
**AP(>=3)** over the stopping slice with **AUC(>=3)** as the fallback where the
slice holds one class. [`INHERITANCE`] lists what came across and what did not,
because "the same recipe" is a claim a reader has to be able to check.

Three things moved and each is declared there rather than discovered in the
numbers: the source geometry, the batch stratification, and the split seed.

## The split is ONE split, and that is the change that matters

`render_deploy` draws its 80/20 under the **run's own seed**, so its three seeds
sit on three different stopping slices — which is why `models/render/README.md`
warns that the 0.008 between two of its APs "is not a comparison of two heads".
That is sound for a band whose question is *how does this recipe do*; it is
useless for a grid whose question is *which arm*.

So [`SPLIT_SEED`] is fixed and every arm and every seed reads the same sides. The
training seed moves the initialisation's dropout draw and the sampler's order and
nothing else, and every run of the grid is read on identical rows.

**The 20% is the stopping slice and it is also the only held-out number there
is.** That is the shipped recipe's own trade, carried: the holdout's one job is
to stop the run. Every AP and AUC below is therefore optimistic by exactly one
early stop, it is *within-store* held out, and the store is not eval-eligible —
its population is 700 seats plus 300 runners-up at one location apiece with no
colour-ceiling representation, so no number here is a base rate about anything.

## Stratified by batch, because the three sittings are three scales

The first sitting's three batches disagree at chi-square 30.95 on 6 d.f.,
**p = 2.6e-05**: the 1s fall away 17 -> 6 -> 3 as the labeler finds the floor and
the third piles onto 3 at the expense of 4. The strata were near-identical by
construction, so that is the scale moving and not the draw.

A lineage is the hard constraint and the batch is the soft one: groups are taken
whole, and the holdout is filled by whichever remaining group most reduces the
per-batch shortfall. `batch` is a covariate and is never handed to the model.

## How much trunk to unfreeze is measured, not argued

Three arms, in [`ARMS`]. The parameter shares are worth having in front of you
before reading the table, because this backbone is top-heavy: `conv_head` alone
is **1,228,800** of its 2,496,867 parameters, so "just the last block" is already
more than half the net.

```text
frozen       classifier only                            3,843    0.15%
last_block   + blocks[4], conv_head, norm_head      1,360,003   54.5%
more         everything                             2,496,867  100.0%
```

**A frozen module is put in `eval()` for the pass as well**, so its batch-norm
running statistics do not move. A "frozen" trunk whose normalisation kept
adapting is a trunk that trained, quietly, and the arm would be measuring
something nobody named.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from fractal_wallpapers import storage
from fractal_wallpapers.models import head
from fractal_wallpapers.paths import repo_root, tracked_name, under

#: The schema every record here carries.
SCHEMA = 1

#: What this head is called, everywhere it is named. The store's own name, because
#: the corpus is what makes it a different head — not [`roster.HEADS`], which is
#: what a release carries, and this ships nothing.
HEAD = "gallery_grade"

#: The shipped artifact this head starts from, relative to the checkout.
SOURCE = Path("models") / "render" / "render.fp16.pt"

#: The 80/20 over lineages, and the seed it is drawn under. **Fixed**, not the
#: run's — see the module docstring: a grid answering "which arm" has to be read
#: on one slice.
HOLDOUT_SHARE = 0.20
SPLIT_SEED = 0

#: The column the stopping rule ranks by, the boundary a hit is counted at, the
#: epoch ceiling and the patience — [`render_deploy`]'s four, and the shipped
#: judge's.
#:
#: **Written down rather than imported, and that is the one thing in this module
#: that is a copy.** Everything below `import` here is stdlib, so that a base
#: install can build the command line: `render_deploy` reaches `metrics`, which
#: reaches numpy, and one constant imported from the wrong module is all it takes
#: to put two gigabytes of CUDA wheels on the `fetch-weights --check` path — which
#: is exactly how that property was lost once already, and what
#: `tests/test_base_install.py` exists to catch. `tests/test_gallery_grade_train.py`
#: holds these four to `render_deploy`'s, so the copy cannot drift in silence.
RANK_COLUMN, HIT_TIER = "p_ge3", 3
EPOCHS = 20
PATIENCE = 6

#: The stopping rules a band may run under, by the name every record calls one.
#:
#: `ap_ge3` is the shipped judge's, carried whole for the first band. It is the
#: **wrong boundary for this head** and the first band is what showed it: an order
#: inside the gate's own top is 3-against-4, and `last_block_seed0` peaked
#: `AUC(>=4)` at 0.66 on an epoch whose `AP(>=3)` had dipped, so the rule and the
#: job disagree within a single run.
#:
#: `auc_ge4` is this head's own, and it is rank-only at the boundary the seating
#: cares about. Matt's call of 2026-09-06.
RULES: dict[str, dict] = {
    "auc_ge4": {
        "statistic": "auc",
        "tier": 4,
        "says": (
            "max AUC(>=4) over the stopping slice, ranked by p_ge4. Rank-only, at the "
            "boundary a seating inside the gate's own top actually orders on"
        ),
    },
    "ap_ge3": {
        "statistic": "average_precision",
        "tier": HIT_TIER,
        "says": (
            "max AP(>=3) over the stopping slice, ranked by p_ge3 — the shipped render "
            "judge's rule, carried whole. Superseded here: it is not this head's boundary"
        ),
    },
}

#: The band the first six runs were fitted under, and the one every run since is.
#:
#: **The first band's directories keep their bare `<arm>_seed<N>` names**, for
#: [`render_deploy.run_name`]'s reason: their records are on disk under them and
#: renaming would make every report quoting `more_seed1` wrong about a run that
#: still exists. Every later band prefixes its own name.
FIRST_BAND = "ap_ge3"
BAND = "auc_ge4"

#: The corpora a band may be fitted over. **A corpus is WHICH ROWS and a band is
#: WHICH STOPPING RULE**, and they are two axes rather than one: a refit on more
#: labels under an unchanged rule is a different corpus, not a different band.
#:
#: They are separate because the population join and the split are written down
#: once and every run of a grid reads them. Re-fitting on a grown store under the
#: same name would overwrite the file the adopted run's own `split` block names,
#: and the run on disk would stop being reproducible without anything looking
#: broken.
#:
#: `batches` is the store's own batch names, or `None` for *every graded row*.
#: The build corpus lists its three rather than saying "not the new one", so that
#: re-running its population a year from now gives the file it gave then.
CORPORA: dict[str, dict] = {
    "as_built": {
        "batches": ("n1000_0906_1", "n1000_0906_2", "n1000_0906_3"),
        "says": (
            "the three sittings of 2026-09-06 — the thousand rows this head was built on "
            "and adopted on"
        ),
    },
    "corrected": {
        "batches": None,
        "says": (
            "every graded row the store holds, the correction sitting of 2026-09-09 "
            "included. Its rows are not comparable with the build corpus's: the split is "
            "redrawn over everything, so no slice of one is a slice of the other"
        ),
    },
    "twelve_sheets": {
        "batches": None,
        "frozen": True,
        "says": (
            "the 2,829 rows over twelve labelling sheets the store held on 2026-09-10 — "
            "the two gallery sittings and the augmentation sweep's two sheets on top of "
            "`corrected`'s. FROZEN: its join, its split and its targets are tracked under "
            "`data/gallery_grade/corpus/twelve_sheets/` rather than regenerable, because "
            "the join reads the LIVE store and cannot give these rows back once another "
            "sheet is graded"
        ),
    },
}

#: The corpora whose files are tracked rather than regenerable, and read from
#: `data/gallery_grade/corpus/<name>/` rather than from [`root`].
#:
#: **One corpus is frozen and that is not a pattern to follow.** A corpus that the
#: population command will rebuild belongs under the regenerable tree with every
#: other; this one is kept because a shipped column was fitted on it and the
#: command that made it no longer can. `data/gallery_grade/corpus/README.md`
#: carries the decision and `tests/test_history_purity.py` the size exemption two
#: of its files need.
FROZEN_CORPUS_DIR = Path("data") / "gallery_grade" / "corpus"


#: The corpus whose files carry the **bare** names, for [`FIRST_BAND`]'s reason
#: turned onto the other axis: `population.jsonl`, `split.json` and
#: `auc_ge4_more_seed2/` are on disk under those names and are what every record
#: written before 2026-09-09 refers to. Every later corpus suffixes its own.
BUILD_CORPUS = "as_built"

#: What an unflagged verb here means, and it is **the ADOPTED corpus** rather
#: than the newest one. `score-pool` writes the column a seating orders on, so a
#: default pointing at a staged refit would let an adoption happen by forgetting
#: a flag. Moving this constant is part of adopting a refit and is Matt's call,
#: not a tidy-up.
#:
#: **Moved to `corrected` on 2026-09-09**, Matt's ruling, adopting
#: `corrected_auc_ge4_more_seed1` — `more`, the median seed, epoch 6 — which
#: cleared its pre-registered bar 12 of 12 at worst margin +0.085. The adopting
#: act is three things and this constant is only the first: the pool was
#: re-scored through that run and `solve.DEFAULT_FINE_BAR` moved 0.50 -> 0.184 to
#: hold the admitted fraction where it was. `models/gallery_grade/README.md`'s
#: *Adopted 2026-09-09* carries what the move does and does not mean.
#:
#: **Moved to `twelve_sheets` on 2026-09-10**, Matt's ruling, adopting the
#: `drop_high_asymmetric` k=3 ensemble over seeds 0/1/2 — the gallery he approved
#: off `deterministic_refit_20260910`'s browse page. The adopting act is the same
#: three things and this constant is still only the first.
CORPUS = "twelve_sheets"

#: The arms this band runs. **Two, not three**: `frozen` read 0.492 and 0.496 on
#: `AUC(>=4)` in the first band — chance, and below the judge's own 0.528 — so a
#: linear read of the frozen trunk has nothing to say about the boundary this band
#: stops on, and fitting it again would buy a third row saying so.
BAND_ARMS = ("last_block", "more")

#: The seeds a band runs. Three, which is every other band here; the first band
#: ran **two** on Matt's call and its records say so on each row.
#:
#: The split is fixed across a whole grid, so a seed moves the initialisation's
#: dropout draw and the sampler's order and nothing else. The third seed is what
#: makes [`band`]'s **median** pick possible, and a median is the point rather
#: than a nicety: `more`'s AP surface across epochs is flat enough that cuDNN's
#: own nondeterminism decides the argmax, so shipping the best seed would ship a
#: coin flip. The median is the seed the band would give again.
SEEDS = (0, 1, 2)

#: How much trunk each arm unfreezes, as the `timm` child modules whose parameters
#: take a gradient. The classifier is in every arm because a head that trained
#: nothing would not be a head.
#:
#: `more` is **everything**, and that is a choice rather than the obvious reading
#: of the word. Three points spanning 0.2%, 54.4% and 100% of the parameters is a
#: wider span than any interior cut would give, and the full fine-tune is the arm
#: most at risk on a training side of a few hundred pictures — which is the risk
#: this comparison exists to price.
ARMS: dict[str, dict] = {
    "frozen": {
        "unfrozen": ("classifier",),
        "says": "the trunk is a fixed feature extractor; only the ordinal classifier learns",
    },
    "last_block": {
        "unfrozen": ("blocks.4", "conv_head", "norm_head", "classifier"),
        "says": (
            "the last block stage and the pointwise head above it. Half the net by "
            "parameter count, because conv_head alone is 49% of this backbone"
        ),
    },
    "more": {
        "unfrozen": (),  # empty means: nothing is frozen
        "says": "a full fine-tune — every parameter takes a gradient",
    },
}

#: The recipes a band may be fitted under. **A corpus is WHICH ROWS, a band is
#: WHICH STOPPING RULE, and a recipe is WHICH KNOBS** — three axes rather than
#: one, for [`CORPORA`]'s reason carried one step further: two arms fitted under
#: different dropout are not two arms, and a grid that mixed them would answer a
#: question nobody asked.
#:
#: `inherited` is the shipped judge's, carried whole — [`INHERITANCE`] lists what
#: came across — and it is what every run before 2026-09-10 was fitted under, so
#: its runs keep bare names for [`FIRST_BAND`]'s reason.
#:
#: `drop_high_asymmetric` is `best_head_20260910`'s winning column, adopted
#: 2026-09-10. Four knobs move and each was measured before it was taken:
#:
#: * **`drop_high`** — dropout 0.4, stochastic depth 0.2. `augmentation_sweep_
#:   20260910` ran eleven arms and this is the only one that won every column.
#: * **the 2x negative weighting** — every CORN cutpoint's negative term is
#:   upweighted, which is exactly *do not let a row that stopped at tier k cross
#:   above k*: cutpoint k is trained only on the rows that reached it, and its
#:   negatives are precisely the rows whose grade IS k. The loss stays a weighted
#:   **mean**, so the arm is not also a learning-rate sweep.
#: * **a fixed horizon and no early stop** — 30 epochs, patience above it, the
#:   epoch taken at the best AUC(>=4) wherever on the curve it falls. The loss
#:   rule buys a reproducible epoch at the cost of a less reproducible column.
#: * **a learned per-batch offset on the logit**, centred at every use so it is
#:   identified, no weight decay, and **dropped at inference** — so the column a
#:   seating reads is on one scale, the average sitting's.
#:
#: It ships an **ensemble of every seed**, averaged on the probability scale,
#: rather than the band's median run: `stability_and_sheet_20260910` measured
#: churn falling as `0.108 + 0.657/sqrt(k)` with no knee.
RECIPES: dict[str, dict] = {
    "inherited": {
        "arms": BAND_ARMS,
        "ensemble": False,
        "ships": "the band's median seed",
        "says": "the shipped render judge's recipe, carried whole",
    },
    "drop_high_asymmetric": {
        "arms": ("more",),
        "ensemble": True,
        "ships": "every seed, averaged on the probability scale",
        "drop_rate": 0.4,
        "drop_path_rate": 0.2,
        "neg_weight": 2.0,
        "epochs": 30,
        "patience": 999,
        "offset": "batch",
        "checkpoint": "auc_ge4",
        "workers": 6,
        "says": (
            "dropout 0.4 and stochastic depth 0.2, every cutpoint's negative term at 2x, a "
            "fixed 30-epoch horizon with the AUC(>=4) checkpoint, and a learned per-batch "
            "offset dropped at inference. Ships k seeds averaged on the probability scale"
        ),
    },
}

#: What an unflagged verb here means on the recipe axis, and it is the recipe the
#: SHIPPED column was fitted under. [`CORPUS`]'s rule, on the third axis: a
#: default pointing at a staged recipe would let an adoption happen by forgetting
#: a flag.
#:
#: **Moved to `drop_high_asymmetric` on 2026-09-10**, Matt's ruling, adopting the
#: k=3 ensemble of seeds 0/1/2 over [`CORPUS`] `twelve_sheets`.
RECIPE = "drop_high_asymmetric"

#: The recipe whose runs carry **bare** names, for [`FIRST_BAND`]'s reason on the
#: third axis: every run fitted before 2026-09-10 is on disk without one.
FIRST_RECIPE = "inherited"


class GradeTrainingError(RuntimeError):
    """A fine-tier head that cannot be fitted or read on what is here."""


def say(*parts) -> None:
    """[`train.say`], reached lazily so this module imports on a base install.

    It is the default `log` of every entry point here, and a default argument is
    evaluated at import — so `log=say` would be the numpy import this
    module is arranged to avoid, written as a default rather than as an import.
    """
    from fractal_wallpapers.models import train

    train.say(*parts)


# --------------------------------------------------------------------------- #
# Where things live.
# --------------------------------------------------------------------------- #
def head_dir(run: str | None = None) -> Path:
    """Where a run's checkpoints and records land. Beside the shipped heads.

    Not on [`roster.HEADS`], so no release carries it and `fetch-weights` never
    asks for it; the `.pt` files are ignored by the same `models/**/*.pt` rule
    every other head's are, so the weights stay out of history while the records
    that describe them do not.
    """
    base = repo_root() / "models" / HEAD
    return base / run if run else base


def check_corpus(corpus: str) -> str:
    if str(corpus) not in CORPORA:
        raise GradeTrainingError(f"{corpus!r} is not a corpus; the two are {sorted(CORPORA)}")
    return str(corpus)


def qualified(stem: str, corpus: str = CORPUS) -> str:
    """`stem` for the build corpus, `<corpus>_<stem>` for every later one.

    The one place the corpus enters a name, so that a file, a run directory and a
    bar all say the same thing about which rows they are about.
    """
    return stem if check_corpus(corpus) == BUILD_CORPUS else f"{corpus}_{stem}"


def check_recipe(recipe: str) -> str:
    if str(recipe) not in RECIPES:
        raise GradeTrainingError(f"{recipe!r} is not a recipe; they are {sorted(RECIPES)}")
    return str(recipe)


def frozen(corpus: str) -> bool:
    """Whether this corpus's files are tracked rather than regenerable."""
    return bool(CORPORA[check_corpus(corpus)].get("frozen"))


def frozen_dir(corpus: str) -> Path:
    """Where a frozen corpus's five files live. Tracked, and read-only to this module."""
    return repo_root() / FROZEN_CORPUS_DIR / check_corpus(corpus)


def run_name(
    arm: str, seed: int, band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE
) -> str:
    """`<corpus>_<recipe>_<band>_<arm>_seed<N>`, each leading part dropped at its default.

    The first band's names are bare because they were written before there was a
    second one and its records are on disk under them — [`FIRST_BAND`] says why
    renaming them would be worse than the asymmetry, and [`BUILD_CORPUS`] and
    [`FIRST_RECIPE`] say the same about the other two axes.
    """
    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")
    if str(band) not in RULES:
        raise GradeTrainingError(f"{band!r} is not a band; the two are {sorted(RULES)}")
    stem = f"{arm}_seed{int(seed)}"
    if str(band) != FIRST_BAND:
        stem = f"{band}_{stem}"
    if check_recipe(recipe) != FIRST_RECIPE:
        stem = f"{recipe}_{stem}"
    return qualified(stem, corpus)


def run_dir(
    arm: str, seed: int, band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE
) -> Path:
    return head_dir(run_name(arm, seed, band, corpus, recipe))


def root() -> Path:
    """The regenerable tree this fit's own readouts land in.

    Its own top-level name and **not** `artifacts/gallery_grade`, which holds the
    sheets' plans — the only thing that can rebuild a levelled picture as it was
    judged, and protection-held for that reason. A regenerable readout does not
    go into a subtree somebody has to be careful about deleting.
    """
    return under("gallery_grade_head")


def population_path(corpus: str = CORPUS) -> Path:
    """A frozen corpus's join is tracked; every other one's is regenerable."""
    if frozen(corpus):
        return frozen_dir(corpus) / "population.jsonl"
    return root() / f"{qualified('population', corpus)}.jsonl"


def split_path(corpus: str = CORPUS) -> Path:
    if frozen(corpus):
        return frozen_dir(corpus) / "split.json"
    return root() / f"{qualified('split', corpus)}.json"


def _banded(stem: str, band: str, recipe: str, bare_first_band: bool = False) -> str:
    """`<recipe>_<stem>_<band>`, each part dropped at its default. One spelling.

    `bare_first_band` is [`band_path`]'s alone and is the asymmetry `band.json` is
    on disk under: the bar and its read were written after there was a second
    band and have always carried its name.
    """
    named = stem if (bare_first_band and str(band) == FIRST_BAND) else f"{stem}_{band}"
    return named if check_recipe(recipe) == FIRST_RECIPE else f"{recipe}_{named}"


def band_path(band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE) -> Path:
    return root() / f"{qualified(_banded('band', band, recipe, True), corpus)}.json"


def bar_path(band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE) -> Path:
    """Where a band's PRE-REGISTERED bar lives. Tracked, beside the run records.

    The first band has none and never will: it was a build, its rule was the
    shipped judge's, and a bar written after the fact is a bar fitted to what
    happened.
    """
    return head_dir() / f"{qualified(_banded('bar', band, recipe), corpus)}.json"


def comparison_path(band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE) -> Path:
    """Where the bar's READ lives — what the band actually did against it."""
    return head_dir() / f"{qualified(_banded('comparison', band, recipe), corpus)}.json"


# --------------------------------------------------------------------------- #
# The population: a grade, and the candidate picture it was cast about.
# --------------------------------------------------------------------------- #
@dataclass
class Unit:
    """One training unit: a grade, and the ledger's 640x360 picture of that recipe.

    **[`finished_train.Picture`]'s fields, by name, and not its subclass.** The
    sampler, the class balance and the histogram are that module's and are reached
    unchanged — they read `.path`, `.score` and `.place` off whatever they are
    handed — but inheriting would mean importing it to *define* this class, and
    everything at this module's top level is stdlib so that a base install can
    build the command line. The duck-typed shape is all any of them needs, which
    is the argument [`finished_train.Crops`] already makes about `torch.Dataset`.

    ⚠ **The `score` field carries a GRADE**, and the two are different estimands —
    `data/gallery_grade/README.md`'s *This is not a fifth judge, and its 1 is not
    anybody's 1*. The field keeps that name because the sampler and the histogram
    read it, and re-typing a sampler to rename a field would measure the
    re-typing. The rename happens exactly once, in [`population`], and nothing
    downstream of it writes a store.

    `key` is the ledger key, which is also what the seeded per-picture jitter is
    drawn on through the parent's `name`.

    **The two judge readings are carried and are two different numbers.**
    `label_p_ge*` is the shipped judge on the 1280x720 sheet picture the verdict
    was cast on; `candidate_p_ge*` is `selected_on` — the same judge on the
    640x360 row a mining pass scored, which is both the picture this head is
    trained on and the column a seating walks. They correlate at r = 0.696 over
    the store, which is far too low for either to stand in for the other, so a
    baseline quoting one of them has to say which.
    """

    # [`finished_train.Picture`]'s eight, in its order and by its names.
    path: Path
    score: int
    side: str
    batch: str
    place: str
    partition: str
    mode: str
    name: str
    # And this store's own.
    key: str = ""
    #: The ledger row's own location key, carried because the shipped `rank_key`
    #: reads the location head's `P(>=4)` for the place and this is the only
    #: thing that joins a unit to it. It is the ledger's spelling and not
    #: [`place`]'s, which is the label store's tuple.
    location: str = ""
    #: The **cut** a verdict was cast on, and the **block** of the draw it came
    #: from. Both are covariates the split balances and neither is ever shown to
    #: the model — `data/batch_caveats.md`'s *The sheet is a covariate* is why
    #: they are carried at all: the correction sitting's three sheets disagree at
    #: chi-square 69.39 over its 750 rows, so a fold that took them unevenly
    #: would move a recall gap for a reason that is not fit.
    #:
    #: They fall back rather than being absent: a row from before the blocked
    #: draws reads `pre_existing`, and a store that names no sheet reads its
    #: batch, which is what those sittings' sheets were called anyway.
    block: str = ""
    sheet: str = ""
    leveled: bool = False
    seated: bool = False
    label_p_ge3: float | None = None
    label_p_ge4: float | None = None
    candidate_p_ge3: float | None = None
    candidate_p_ge4: float | None = None


#: What a row from before the blocked draws calls its block. One value and not
#: `None`, because it is a stratum the split balances and a missing stratum is a
#: shortfall nothing can be measured against.
PRE_EXISTING = "pre_existing"


def block_of(row: dict) -> str:
    """Which block of a blocked draw this verdict came from, or [`PRE_EXISTING`]."""
    drawn = row.get("selected_on") or {}
    return str(drawn.get("block") or PRE_EXISTING)


def sheet_of(row: dict) -> str:
    """The cut a verdict was cast on, falling back to the batch that holds it."""
    return str(row.get("sheet") or row.get("batch") or "")


def population(corpus: str = CORPUS, log=say) -> tuple[list[Unit], dict]:
    """Every graded row, joined to the ledger row whose picture it was cast about.

    One streaming pass over the ledger, which is the largest store here and is
    read a line at a time for [`curation.rank_key`]'s reason: the join needs four
    fields a row and parsing four hundred megabytes into dictionaries costs many
    times its own size for them.

    A row that will not resolve is **dropped and counted with its reason** rather
    than repaired: the store is append-only and the ledger is the authority on
    what is on disk.
    """
    from fractal_wallpapers.curation import candidate_ledger, retention
    from fractal_wallpapers.labeling import gallery_grade
    from fractal_wallpapers.models import finished_train
    from fractal_wallpapers.paths import Tiers, rehome

    held = CORPORA[check_corpus(corpus)]["batches"]
    graded = gallery_grade.resolved().graded()
    if held is not None:
        graded = [row for row in graded if str(row.get("batch")) in set(held)]
        if not graded:
            raise GradeTrainingError(
                f"corpus {corpus!r} names batches {sorted(held)} and the store holds no "
                f"graded row from any of them"
            )
    wanted: dict = {}
    unkeyed = 0
    for row in graded:
        key = gallery_grade.render_key(row)
        if key is None:
            unkeyed += 1
            continue
        wanted.setdefault(key, []).append(row)

    ledger = candidate_ledger.rows_path()
    if not ledger.is_file():
        raise GradeTrainingError(f"{ledger} is not there — run `curate candidate-ledger backfill`")

    found: dict = {}
    scanned = 0
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            scanned += 1
            stored = json.loads(line)
            key = retention.render_key_of(stored)
            if key is not None and key in wanted:
                found.setdefault(key, []).append(stored)
    log(f"[{HEAD}] {scanned:,} ledger rows scanned for {len(wanted):,} graded render keys")

    tiers = Tiers.current()
    units: list[Unit] = []
    dropped = {"unkeyed": unkeyed, "no_ledger_row": 0, "no_picture": 0, "picture_absent": 0}
    ambiguous = 0
    for key, rows in wanted.items():
        carriers = found.get(key) or []
        if not carriers:
            dropped["no_ledger_row"] += len(rows)
            continue
        if len(carriers) > 1:
            ambiguous += 1
        # Deterministic where a key is carried by more than one row: the ledger
        # key sorts, and a later leg re-rendering one of these recipes at another
        # regime is the harmless direction the retention guard already names.
        stored = sorted(carriers, key=lambda held: str(held.get("key")))[0]
        named = stored.get("picture")
        if not named:
            dropped["no_picture"] += len(rows)
            continue
        where = rehome(str(named), tiers)
        if where is None or not where.is_file():
            dropped["picture_absent"] += len(rows)
            continue
        for row in rows:
            reading = row.get("reading") or {}
            drawn = row.get("selected_on") or {}
            units.append(
                Unit(
                    path=where,
                    score=int(row["grade"]),
                    side="",
                    batch=str(row["batch"]),
                    place=repr(gallery_grade.place_of(row)),
                    partition=row.get("partition") or "",
                    mode=str(row["mode"]),
                    name=str(stored.get("key")),
                    key=str(stored.get("key")),
                    location=str((stored.get("location") or {}).get("key") or ""),
                    block=block_of(row),
                    sheet=sheet_of(row),
                    leveled=bool(row.get("leveled")),
                    seated=bool(row.get("seated")),
                    label_p_ge3=reading.get("p_ge3"),
                    label_p_ge4=reading.get("p_ge4"),
                    candidate_p_ge3=drawn.get("p_ge3"),
                    candidate_p_ge4=drawn.get("p_ge4"),
                )
            )

    storage.require_hot(*{unit.path.parent for unit in units}, what="fitting the fine-tier head")

    record = {
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "graded_rows": len(graded),
        "render_keys": len(wanted),
        "ledger_rows_scanned": scanned,
        "ledger_path": tracked_name(ledger),
        "resolved": len(units),
        "dropped": dropped,
        "keys_carried_by_more_than_one_ledger_row": ambiguous,
        "geometry": "the ledger's stored 640x360 candidate — not the 1280x720 sheet picture",
        "batches": _counted(unit.batch for unit in units),
        "blocks": _counted(unit.block for unit in units),
        "sheets": _counted(unit.sheet for unit in units),
        "grades": finished_train.histogram(units),
        "leveled": sum(1 for unit in units if unit.leveled),
        "seated": sum(1 for unit in units if unit.seated),
        "locations": len({unit.place for unit in units}),
    }
    total_dropped = sum(dropped.values())
    if total_dropped:
        log(f"[{HEAD}] dropped {total_dropped} row(s): {json.dumps(dropped)}")
    if not units:
        raise GradeTrainingError("no graded row resolved to a candidate picture")
    return units, record


def _counted(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


def write_population(corpus: str = CORPUS, log=say) -> tuple[Path, dict]:
    """Resolve the store against the ledger once and keep the answer.

    The ledger pass is the expensive half of a fit and it does not change between
    arms, so it is cached under the regenerable tree and every run reads it.
    """
    if frozen(corpus):
        raise GradeTrainingError(
            f"{corpus!r} is frozen: its join is tracked because the live store has moved "
            f"past it, and rebuilding it here would overwrite the rows a shipped column was "
            f"fitted on with different ones. Name another corpus."
        )
    units, record = population(corpus=corpus, log=log)
    path = population_path(corpus)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "key": unit.key,
                        "location": unit.location,
                        "picture": tracked_name(unit.path),
                        "grade": unit.score,
                        "batch": unit.batch,
                        "block": unit.block,
                        "sheet": unit.sheet,
                        "place": unit.place,
                        "partition": unit.partition,
                        "mode": unit.mode,
                        "leveled": unit.leveled,
                        "seated": unit.seated,
                        "label_p_ge3": unit.label_p_ge3,
                        "label_p_ge4": unit.label_p_ge4,
                        "candidate_p_ge3": unit.candidate_p_ge3,
                        "candidate_p_ge4": unit.candidate_p_ge4,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    (root() / f"{qualified('population', corpus)}.json").write_text(
        json.dumps({"schema": SCHEMA, **record}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path, record


def read_frozen_population(corpus: str) -> list[Unit]:
    """A tracked corpus's join, with the per-render **raw** target as the score.

    Read in its own shape rather than converted on the way in: the file is kept
    byte for byte so that `checksums.json` still checks against the column fitted
    on it, and a reader that needed it re-serialised would be a reader asking for
    the one thing that cannot happen to it.

    ⚠ **The score is not the row's own verdict.** `population.jsonl` carries the
    grade as cast; the band trains on `targets.json`'s per-render `raw`, which is
    that scale de-duplicated over a render's repeat gradings. The `normalized`
    column beside it is a yardstick and never a training target —
    `models/gallery_grade/README.md`'s *What the de-drifted target is for*.
    """
    from fractal_wallpapers.paths import Tiers, rehome

    where = frozen_dir(corpus)
    path = where / "population.jsonl"
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} is not there. A frozen corpus is tracked rather than regenerable — "
            f"`gallery-grade population` will not rebuild it, and `data/gallery_grade/"
            f"corpus/README.md` says why."
        )
    targets = json.loads((where / "targets.json").read_text(encoding="utf-8"))["per_render"]
    render_of = json.loads((where / "render_key_of.json").read_text(encoding="utf-8"))
    tiers = Tiers.current()
    units: list[Unit] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = str(row["key"])
        render = render_of.get(key)
        if render is None or render not in targets:
            raise GradeTrainingError(f"{path}:{number}: {key} has no per-render target")
        units.append(
            Unit(
                path=rehome(row["path"], tiers) or Path(row["path"]),
                score=int(targets[render]["raw"]),
                side="",
                batch=row["batch"],
                place=row["place"],
                partition=row.get("partition") or "",
                mode=row["mode"],
                name=key,
                key=key,
                location=row.get("location") or "",
                block=row.get("block") or PRE_EXISTING,
                sheet=row.get("sheet") or row.get("batch") or "",
                leveled=bool(row.get("leveled")),
                seated=bool(row.get("seated")),
                label_p_ge3=row.get("label_p_ge3"),
                label_p_ge4=row.get("label_p_ge4"),
                candidate_p_ge3=row.get("candidate_p_ge3"),
                candidate_p_ge4=row.get("candidate_p_ge4"),
            )
        )
    return units


def read_population(corpus: str = CORPUS) -> list[Unit]:
    """The cached join, re-homed against this machine's tiers."""
    from fractal_wallpapers.paths import Tiers, rehome

    if frozen(corpus):
        return read_frozen_population(corpus)
    path = population_path(corpus)
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} is not there — run `gallery-grade population` first, so that every arm "
            f"is fitted on one join rather than on its own."
        )
    tiers = Tiers.current()
    units: list[Unit] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise GradeTrainingError(f"{path}:{number}: schema {row.get('schema')!r}")
        units.append(
            Unit(
                path=rehome(row["picture"], tiers) or Path(row["picture"]),
                score=int(row["grade"]),
                side="",
                batch=row["batch"],
                place=row["place"],
                partition=row.get("partition") or "",
                mode=row["mode"],
                name=row["key"],
                key=row["key"],
                location=row.get("location") or "",
                block=row.get("block") or PRE_EXISTING,
                sheet=row.get("sheet") or row.get("batch") or "",
                leveled=bool(row.get("leveled")),
                seated=bool(row.get("seated")),
                label_p_ge3=row.get("label_p_ge3"),
                label_p_ge4=row.get("label_p_ge4"),
                candidate_p_ge3=row.get("candidate_p_ge3"),
                candidate_p_ge4=row.get("candidate_p_ge4"),
            )
        )
    return units


# --------------------------------------------------------------------------- #
# The split: lineages whole, batches balanced.
# --------------------------------------------------------------------------- #
#: What the holdout is balanced on, beyond taking lineages whole. **Marginals,
#: not the cross**: a lineage carries a handful of rows and the cross of three
#: families is mostly empty cells, so a shortfall stated on it would be noise
#: rather than a constraint.
#:
#: * `sheet` — the cut a verdict was cast on, and a **refinement of the batch**:
#:   every sheet sits inside exactly one batch, so balancing sheets balances
#:   batches by summation and the batch is reported rather than balanced. The
#:   three sittings of 2026-09-06 disagree at p = 2.6e-05 and the correction
#:   sitting's own three sheets at chi-square 69.39, so this is the same
#:   constraint the build corpus had, tightened by one level.
#: * `block` — which population of a blocked draw a row came from. The four
#:   blocks are four different questions, and a stopping slice that was mostly
#:   `near_bar` would be measuring a boundary rather than a fit.
#: * `grade` — the label. The blocks' scales run from mean 1.18 to 2.69, so
#:   block balance does not imply grade balance, and a recall read on a slice
#:   short of 4s is read on a handful of rows.
STRATA = ("sheet", "block", "grade")


def strata_of(unit: Unit) -> dict[str, str]:
    """The `{family: value}` this unit counts under, for each of [`STRATA`]."""
    return {
        "sheet": unit.sheet or unit.batch,
        "block": unit.block or PRE_EXISTING,
        "grade": str(unit.score),
    }


def sides_for(units: list[Unit], seed: int = SPLIT_SEED, rows: list[dict] | None = None) -> dict:
    """Put every unit on the side the seeded, stratified 80/20 gives it.

    Lineages are the hard constraint and go whole. Inside that, the holdout is
    filled by whichever remaining lineage most reduces the summed shortfall over
    [`STRATA`]'s marginals — the cuts are different scales, the blocks are
    different populations, and a stopping slice over-weighting any of them would
    be stopping on something the training side is not on.

    ⚠ **A stratum is a covariate the SPLIT reads and the model never does.** No
    sheet term, no reweighting, no exclusion: Matt's ruling of 2026-09-09 is that
    the sheets' disagreement is label noise and stays label noise. What the
    balance buys is that the train-vs-stopping gap moves for fit and not for
    which cuts landed on which side.

    `rows` is the label rows the units came from, in the same order; the grouping
    rule reads a family and a viewport off them and this module does not carry a
    second spelling of either.
    """
    import random

    from fractal_wallpapers.labeling import groups
    from fractal_wallpapers.models import finished_train

    if rows is None:
        rows = label_rows_for(units)
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise GradeTrainingError(
            f"{grouping.n_unplaced} row(s) carry no location identity, so they cannot be "
            f"grouped. A holdout quietly holding ungrouped rows leaks by exactly the amount "
            f"nobody counted."
        )
    lineage = [int(group) for group in grouping.of_row]
    members: dict[int, list[int]] = {}
    for index, group in enumerate(lineage):
        members.setdefault(group, []).append(index)

    # One flat coordinate per (family, value), so the greedy below sums one L1
    # gain over all of [`STRATA`] at once rather than ranking the families
    # against each other — which nothing here could say how to do.
    strata = [strata_of(unit) for unit in units]
    coordinates = sorted({(family, value) for mine in strata for family, value in mine.items()})
    per_stratum = {
        coordinate: sum(1 for mine in strata if mine.get(coordinate[0]) == coordinate[1])
        for coordinate in coordinates
    }
    batches = sorted({unit.batch for unit in units})
    per_batch = {name: sum(1 for unit in units if unit.batch == name) for name in batches}
    target = {name: per_stratum[name] * HOLDOUT_SHARE for name in coordinates}
    wanted = round(len(units) * HOLDOUT_SHARE)

    def vector(group: int) -> dict[tuple, int]:
        out = dict.fromkeys(coordinates, 0)
        for index in members[group]:
            for family, value in strata[index].items():
                out[(family, value)] += 1
        return out

    order = sorted(members)
    random.Random(int(seed)).shuffle(order)
    remaining = list(order)
    held: set[int] = set()
    shortfall = dict(target)
    rows_held = 0
    while rows_held < wanted and remaining:
        # The group that most reduces the L1 shortfall, ties broken by the
        # shuffled order — so the draw is a function of the seed and the corpus.
        best, best_gain = None, None
        for group in remaining:
            counts = vector(group)
            gain = sum(
                abs(shortfall[name]) - abs(shortfall[name] - counts[name]) for name in coordinates
            )
            if best_gain is None or gain > best_gain:
                best, best_gain = group, gain
        held.add(best)
        for name, count in vector(best).items():
            shortfall[name] -= count
        rows_held += len(members[best])
        remaining.remove(best)

    if rows_held >= len(units):
        raise GradeTrainingError("the holdout swallowed the corpus; nothing is left to train on")

    for index, unit in enumerate(units):
        unit.side = "stopping" if lineage[index] in held else "train"

    training = [unit for unit in units if unit.side == "train"]
    stopping = [unit for unit in units if unit.side == "stopping"]
    return {
        "schema": SCHEMA,
        "rule": (
            f"a seeded {1 - HOLDOUT_SHARE:.0%}/{HOLDOUT_SHARE:.0%} over LINEAGES, filled by "
            f"whichever remaining lineage most reduces the summed shortfall over the "
            f"{', '.join(STRATA)} marginals. The holdout's only job is to stop the run — it "
            f"is the shipped judge's split with one seed for every arm, so every run of the "
            f"grid is read on one slice"
        ),
        "unit": "lineage — labeling.groups.assign",
        "seed": int(seed),
        "target_share": HOLDOUT_SHARE,
        "rows": len(units),
        "lineages": len(members),
        "grouping": grouping.summary(),
        "sides": {"train": len(training), "stopping": len(stopping)},
        "holdout_share": round(len(stopping) / len(units), 4),
        "holdout": {"target_rows": wanted, "rows": len(stopping), "lineages": len(held)},
        "strata": _balance(units, stopping),
        "worst_stratum_drift": _worst_drift(units, stopping),
        "batches": {
            "population": per_batch,
            "stopping": _counted(unit.batch for unit in stopping),
            "train": _counted(unit.batch for unit in training),
            "stopping_share_by_batch": {
                name: round(
                    sum(1 for unit in stopping if unit.batch == name) / max(per_batch[name], 1), 4
                )
                for name in batches
            },
            "balanced_by": (
                "the sheet, which refines it — the batch is reported here and is not itself "
                "a coordinate of the fill"
            ),
        },
        "grades": {
            "train": finished_train.histogram(training),
            "stopping": finished_train.histogram(stopping),
        },
        "lineage_of_row": lineage,
        # The side each row landed on, carried so a later run APPLIES this split
        # rather than re-deriving one. Two derivations of one split are two
        # splits the day either input moves, and the whole point of a fixed seed
        # here is that every run of the grid reads the same rows.
        "side_of_row": [unit.side for unit in units],
        "key_of_row": [unit.key for unit in units],
    }


def _balance(units: list[Unit], stopping: list[Unit]) -> dict:
    """What share of each stratum the holdout actually took, family by family."""
    out: dict = {}
    for family in STRATA:
        counts: dict[str, list[int]] = {}
        for unit in units:
            counts.setdefault(strata_of(unit)[family], [0, 0])[0] += 1
        for unit in stopping:
            counts.setdefault(strata_of(unit)[family], [0, 0])[1] += 1
        out[family] = {
            value: {
                "population": population_count,
                "stopping": stopping_count,
                "share": round(stopping_count / max(population_count, 1), 4),
            }
            for value, (population_count, stopping_count) in sorted(counts.items())
        }
    return out


def _worst_drift(units: list[Unit], stopping: list[Unit]) -> dict:
    """The stratum furthest from [`HOLDOUT_SHARE`] — the one number to read first.

    A balance table nobody scans is a balance table, and the fill is greedy over
    lineages taken whole, so it cannot hit every marginal exactly. This is where
    it did worst, so that a split which failed is refused by eye rather than by
    hope.
    """
    balance, worst = _balance(units, stopping), None
    for family, values in balance.items():
        for value, read in values.items():
            drift = abs(read["share"] - HOLDOUT_SHARE)
            if worst is None or drift > worst["drift"]:
                worst = {"stratum": f"{family}={value}", "drift": round(drift, 4), **read}
    return worst or {}


def label_rows_for(units: list[Unit]) -> list[dict]:
    """The store rows the units came from, in the units' order.

    The grouping rule reads a family and a viewport, which live on the label row
    and not on a training unit — so they are fetched from the store rather than
    copied onto the unit, where a stale copy could disagree with the corpus.
    """
    from fractal_wallpapers.labeling import gallery_grade

    by_place: dict[str, dict] = {}
    for row in gallery_grade.resolved().graded():
        by_place.setdefault(repr(gallery_grade.place_of(row)), row)
    out = []
    for unit in units:
        row = by_place.get(unit.place)
        if row is None:
            raise GradeTrainingError(f"no store row for place {unit.place}")
        out.append(row)
    return out


def write_split(seed: int = SPLIT_SEED, corpus: str = CORPUS, log=say) -> tuple[Path, dict]:
    if frozen(corpus):
        raise GradeTrainingError(
            f"{corpus!r} is frozen: re-drawing its sides would put the shipped column's "
            f"training rows into its holdout. Name another corpus."
        )
    units = read_population(corpus)
    record = {"corpus": check_corpus(corpus), **sides_for(units, seed)}
    path = split_path(corpus)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(
        f"[{HEAD}] split: train {record['sides']['train']} / stopping "
        f"{record['sides']['stopping']} over {record['lineages']} lineages; "
        f"worst stratum {record['worst_stratum_drift'].get('stratum')} at "
        f"{record['worst_stratum_drift'].get('share')}"
    )
    return path, record


def read_split(corpus: str = CORPUS) -> dict:
    path = split_path(corpus)
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} does not exist — draw the split before fitting on it, so that every arm "
            f"is read on one slice rather than on its own."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def apply_split(units: list[Unit], document: dict | None = None, corpus: str = CORPUS) -> dict:
    """Put the written split's sides back onto a freshly read population.

    **Applied, never re-derived.** Re-running the draw would give the same answer
    today and a different one the day the store or the ledger moves, and a band
    whose runs quietly sat on two splits would be comparing arms across
    populations. The row order and the keys are both checked, because a file
    agreeing about a length is not a file agreeing about a corpus.
    """
    document = document or read_split(corpus)
    sides = document["side_of_row"]
    keys = document["key_of_row"]
    if len(sides) != len(units):
        raise GradeTrainingError(
            f"the split was drawn over {len(sides)} rows and the population holds "
            f"{len(units)}. Re-draw it: a split read onto a different corpus is not a split."
        )
    disagreeing = [
        index for index, (unit, key) in enumerate(zip(units, keys, strict=True)) if unit.key != key
    ]
    if disagreeing:
        raise GradeTrainingError(
            f"{len(disagreeing)} row(s) of the population are not the rows the split was "
            f"drawn over (first at index {disagreeing[0]}). Re-draw the split."
        )
    for unit, side in zip(units, sides, strict=True):
        unit.side = side
    return document


# --------------------------------------------------------------------------- #
# The recipe, carried out of the shipped artifact.
# --------------------------------------------------------------------------- #
#: The behavioural keys this head takes from `render.fp16.pt`'s own config, read
#: off the file rather than restated — a constant that drifted from the artifact
#: would be a claim of "the same recipe" nobody could check.
CARRIED = (
    "classes",
    "backbone",
    "batch_size",
    "backbone_lr",
    "head_lr",
    "weight_decay",
    "drop_rate",
    "drop_path_rate",
    "grad_clip",
    "amp",
    "border_crop",
    "class_balance",
    "geometry",
    "loss",
    "sampler",
    "selection_cutpoint",
    "target_dims",
    "workers",
)

#: What the recipe inherited, and the three things it did not. "The same recipe"
#: is a claim a reader has to be able to check rather than take.
INHERITANCE = {
    "identical_to_the_shipped_render_judge": list(CARRIED) + ["epochs", "patience", "selection"],
    "chosen": [
        {
            "key": "source_dims",
            "was": "1280x720 — the sheet picture a verdict was cast on",
            "now": "640x360 — the ledger's stored candidate",
            "why": (
                "this head is read where a seating reads, and the two geometries are not "
                "resamplings of each other: they correlate at r = 0.696 over the landed "
                "thousand, with 55 rows under P(>=4) 0.5 at label geometry and none at "
                "candidate geometry. Fitting at the deployment column accepts a label-quality "
                "cost on purpose"
            ),
        },
        {
            "key": "split_stratification",
            "was": "lineages only",
            "now": (
                "lineages whole, and the holdout filled to balance the SHEET, BLOCK and "
                "GRADE marginals"
            ),
            "why": (
                "the cuts a page was cast on are measurably different scales — the three "
                "sittings of 2026-09-06 at p = 2.6e-05 and the correction sitting's own "
                "three sheets at chi-square 69.39 — and a blocked draw's blocks are four "
                "different populations whose means run 1.18 to 2.69. A stopping slice "
                "over-weighting any of them stops on something the training side is not on. "
                "Every one of the three is read by the SPLIT and none is ever shown to the "
                "model: the sheets' disagreement is accepted as label noise, Matt’s "
                "ruling of 2026-09-09, so there is no sheet term, no reweighting and no "
                "exclusion"
            ),
        },
        {
            "key": "split_seed",
            "was": "the run's own seed, so each seed sits on its own slice",
            "now": f"fixed at {SPLIT_SEED} for every arm and every seed",
            "why": (
                "the question here is WHICH ARM, and models/render/README.md says why the "
                "incumbent arrangement cannot answer it: an AP read on two different slices "
                "is not a comparison of two heads. The training seed still moves the "
                "initialisation and the sampler order"
            ),
        },
    ],
    "not_inherited": [
        {
            "key": "pretrained",
            "why": (
                "the backbone is not re-initialised from ImageNet at all — it starts at the "
                "shipped weights-v6 artifact, which is what makes this a second stage rather "
                "than a second judge"
            ),
        },
        {
            "key": "kinds",
            "why": (
                "the render judge is told no kind and this head is told no batch. The "
                "corpus is one store with one scale"
            ),
        },
    ],
}


def source_path() -> Path:
    return repo_root() / SOURCE


def initial_state() -> tuple[dict, dict]:
    """`(the shipped judge's weights, its committed config)` — this head's start.

    Loaded through the same widening every reader of a halved artifact uses: the
    file is fp16 and the head runs in full precision.
    """
    import torch

    path = source_path()
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} is not there. This head is initialised from the shipped render judge — "
            f"run `fractal-wallpapers fetch-weights` before fitting."
        )
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    head.assert_shipped_backbone(path, config)
    return {key: value.float() for key, value in saved["state_dict"].items()}, config


def recipe_from(config: dict) -> dict:
    """The shipped config's behavioural keys, plus this head's three own decisions."""
    missing = [key for key in CARRIED if key not in config]
    if missing:
        raise GradeTrainingError(
            f"the shipped artifact's config is missing {missing}, which this recipe carries "
            f"from it. A recipe that silently defaulted them would not be the one it claims."
        )
    recipe = {key: config[key] for key in CARRIED}
    recipe.update(
        {
            "epochs": EPOCHS,
            "patience": PATIENCE,
            "seed": 0,
            "source_dims": [head.SOURCE_WIDTH, head.SOURCE_HEIGHT],
            "augmentation": (
                "geometric only — border crop and both flips. No colour and no JPEG jitter: "
                "the colouring is what the grade is about"
            ),
            "selection": (
                f"max AP(>={HIT_TIER}) over the stopping slice, ranked by {RANK_COLUMN}, with "
                f"AUC(>={HIT_TIER}) as the fallback where the slice holds one class"
            ),
            "conditioning": "none — the picture is the input, and the head is told no batch",
            "cascade": (
                "stage two behind the render judge's p_ge4. Undefined on a row that never "
                "cleared the gate; never a pool-wide ranker"
            ),
        }
    )
    return recipe


# --------------------------------------------------------------------------- #
# The arms.
# --------------------------------------------------------------------------- #
def freeze(model, arm: str) -> dict:
    """Turn off the gradient everywhere this arm does not unfreeze, and say what it did.

    A module is unfrozen when its name is one of the arm's prefixes or sits under
    one. The empty tuple means nothing is frozen, which is the full fine-tune.
    """
    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")
    prefixes = ARMS[arm]["unfrozen"]
    trainable, total = 0, 0
    for name, parameter in model.named_parameters():
        total += parameter.numel()
        wanted = not prefixes or any(
            name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes
        )
        parameter.requires_grad_(bool(wanted))
        if wanted:
            trainable += parameter.numel()
    return {
        "arm": arm,
        "unfrozen": list(prefixes) or ["<everything>"],
        "says": ARMS[arm]["says"],
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_share": round(trainable / max(total, 1), 4),
    }


def set_train_mode(model, arm: str) -> None:
    """`train()` on the unfrozen part and `eval()` on the rest, every epoch.

    **This is the half of freezing that a `requires_grad` sweep does not do.** A
    batch-norm module in training mode keeps updating its running mean and
    variance whether or not its affine parameters take a gradient, so a "frozen"
    trunk left in `train()` adapts to the new corpus through its normalisation —
    quietly, and the arm would be measuring something nobody named.

    **Two passes, and the order is the whole of it.** `Module.eval()` applies to a
    module *and every descendant*, so a single pass that walked `named_modules()`
    eval-ing whatever did not match would eval `blocks` on its way past — taking
    `blocks.4` down with it — and then skip `blocks.4` for matching. The unfrozen
    roots are therefore put back into training mode afterwards, by name.
    """
    model.train()
    prefixes = ARMS[arm]["unfrozen"]
    if not prefixes:
        return
    for name, module in model.named_modules():
        if not name:
            continue
        if not any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            module.eval()
    named = dict(model.named_modules())
    for prefix in prefixes:
        if prefix in named:
            named[prefix].train()


# --------------------------------------------------------------------------- #
# The loader.
# --------------------------------------------------------------------------- #
class Pictures:
    """The training set over the pool's own JPEGs.

    **[`finished_train.Crops`]'s shape rather than its subclass**, for that class's
    own reason turned one step further: it is duck-typed because subclassing
    `torch.utils.data.Dataset` would mean importing torch to *define* it, and this
    module is arranged so that even `finished_train` is not imported to define
    anything. Defined at module level, though, and that is not negotiable — a
    Windows loader worker is spawned rather than forked, so the dataset is pickled
    and re-imported by name, and a class defined inside a function has no name for
    the child to find.

    It reads the JPEG directly where its shape-mate reads through
    [`renders.open_picture`], because that function answers out of the *render
    cache's* decoded sidecars and these pictures are the candidate pool's: the
    fast path would never hit, and the stat that misses it would be paid a million
    times over a band.
    """

    def __init__(self, rows: list[Unit], transform) -> None:
        self.rows = rows
        self.transform = transform
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        import random

        from PIL import Image

        row = self.rows[index]
        with Image.open(row.path) as opened:
            opened.load()
            image = opened.convert("RGB")
        # Seeded on the picture and the epoch, so a run reproduces and a picture
        # still gets a different crop every pass.
        return self.transform(image, random.Random(f"{row.name}:{self.epoch}")), row.score, index


def _loader(units: list[Unit], transform, recipe: dict, where: str):
    """The shipped judge's loader, over these rows. Sampler and weights are its."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    from fractal_wallpapers.models import finished_train

    examples = Pictures(units, transform)
    raw, mass = finished_train.weights(units)
    sampler = WeightedRandomSampler(
        torch.tensor(raw, dtype=torch.double), num_samples=len(units), replacement=True
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


# --------------------------------------------------------------------------- #
# The stopping rule.
# --------------------------------------------------------------------------- #
def readable_at(labels, tier: int) -> bool:
    """Whether a slice holds **both** classes at `tier`, so a rank statistic exists.

    **This is asked once, before a fit, and never inside the loop.** The first
    band carried a per-epoch fallback and it could not fire:
    [`metrics.average_precision`] and [`metrics.auc`] return `None` under exactly
    one condition and it is the same condition — this one — so a slice either has
    a rank statistic at a boundary for every epoch or for none of them. A branch
    that cannot be reached is worse than no branch, because a reader assumes it
    fired; the question belongs here, where it is answered once and recorded.
    """
    held = {int(label) >= int(tier) for label in labels}
    return len(held) == 2


def objective(labels, probabilities, rule: str = BAND) -> tuple[float, str]:
    """`(what to MINIMIZE, the rule that produced it)` under one of [`RULES`].

    Negated so the loop keeps one convention, and the rule is returned beside the
    number because a run that changed objective mid-band would otherwise stop on
    its patience and call the result a choice.

    **No fallback.** [`readable_at`] settles whether the boundary can be read at
    all, before the fit starts, and a run whose slice cannot carry its rule is
    launched under the other one with that written into its record.
    """
    from fractal_wallpapers.models import metrics

    said = RULES.get(str(rule))
    if said is None:
        raise GradeTrainingError(f"{rule!r} is not a stopping rule; the two are {sorted(RULES)}")
    import numpy

    tier = int(said["tier"])
    hits = (numpy.asarray(labels) >= tier).astype(int)
    # Ranked on the boundary's own column: a statistic at `>=k` read off an
    # ordering by `P(>=k)` is one question asked once, where ranking on one
    # cutpoint and scoring on another is two. `render_deploy` says the same.
    scores = numpy.asarray(probabilities)[:, tier - 2]
    read = getattr(metrics, said["statistic"])(hits, scores)
    if read is None:
        raise GradeTrainingError(
            f"the stopping slice cannot be read at >={tier}, which `readable_at` is asked "
            f"before a fit precisely so that this cannot happen inside the loop"
        )
    return -float(read), str(rule)


# --------------------------------------------------------------------------- #
# `drop_high_asymmetric`: the loss, the pictures, and the eval slice.
# --------------------------------------------------------------------------- #
def weighted_corn_loss(logits, ranks, num_classes: int = 4, neg_weight: float = 1.0):
    """[`head.corn_loss`] with the NEGATIVE side of each cutpoint upweighted.

    Under CORN, cutpoint `k` is trained only on the rows that reached it, so its
    negatives are exactly the rows whose grade **is** `k`. Upweighting them is
    therefore precisely *do not let a row that stopped at tier k cross above k* —
    the asymmetry stated in the loss rather than in a threshold.

    Each cutpoint stays a weighted **mean** and the cutpoints are averaged, so
    moving `neg_weight` is not also a learning-rate sweep.

    At `neg_weight = 1.0` this is [`head.corn_loss`] exactly, and
    [`assert_symmetric_case`] asserts that rather than this docstring claiming it.
    """
    import torch.nn.functional as functional

    total = logits.new_zeros(())
    tasks = num_classes - 1
    for cutpoint in range(tasks):
        subset = ranks > (cutpoint - 1)
        if subset.sum() < 1:
            continue
        target = (ranks[subset] > cutpoint).float()
        predicted = logits[subset, cutpoint]
        weight = target + neg_weight * (1.0 - target)
        log_sigmoid = functional.logsigmoid(predicted)
        per_row = log_sigmoid * target + (log_sigmoid - predicted) * (1.0 - target)
        total = total + -(weight * per_row).sum() / weight.sum()
    return total / tasks


def unweighted_corn_loss(logits, ranks, tasks: int = 3) -> float:
    """The CORN loss over a whole slice at once, in numpy, **unweighted always**.

    Unweighted whatever the recipe: it is the comparison number on the stopping
    slice, and a loss read under each recipe's own weighting would be three
    different quantities wearing one name.
    """
    import numpy

    logits = numpy.asarray(logits, dtype=float)
    ranks = numpy.asarray(ranks, dtype=int)
    total, counted = 0.0, 0
    for cutpoint in range(tasks):
        subset = ranks > (cutpoint - 1)
        if subset.sum() < 1:
            continue
        target = (ranks[subset] > cutpoint).astype(float)
        predicted = logits[subset, cutpoint]
        log_sigmoid = -numpy.logaddexp(0.0, -predicted)
        loss = -(log_sigmoid * target + (log_sigmoid - predicted) * (1.0 - target)).sum()
        total += loss / subset.sum()
        counted += 1
    return float(total / max(counted, 1))


def assert_symmetric_case() -> None:
    """`neg_weight = 1` is the shipped loss, to floating point. Asserted, not assumed.

    Run at the top of every fit under this recipe, where it costs microseconds and
    stands between a silent re-derivation and a band nobody can compare with the
    one beside it.
    """
    import torch

    torch.manual_seed(0)
    logits = torch.randn(64, 3)
    ranks = torch.randint(0, 4, (64,))
    mine = weighted_corn_loss(logits, ranks, 4, 1.0)
    theirs = head.corn_loss(logits, ranks, num_classes=4)
    if not torch.allclose(mine, theirs, atol=1e-6):
        raise GradeTrainingError(
            f"the weighted loss is not the shipped one at neg_weight 1.0: {mine} vs {theirs}"
        )


class SittingPictures:
    """[`Pictures`] plus the **sitting** each row's verdict was cast in.

    The sitting is the offset's coordinate and never an input: the model is shown
    the picture, and a learned scalar per sitting is added to its logits during
    training and dropped at inference.

    Module level for [`Pictures`]'s reason — a Windows loader worker is spawned
    and finds the class by name — and the epoch counter is **shared memory** for
    the same one turned one step further: this recipe's loader is persistent, so
    a plain integer set in the parent would never reach a worker and every epoch
    would silently redraw the crop it drew at epoch zero.
    """

    def __init__(self, rows: list[Unit], transform, groups: list[int], augment: bool) -> None:
        import torch

        self.rows = rows
        self.transform = transform
        self.groups = groups
        self.augment = augment
        self.epoch = torch.zeros((), dtype=torch.long).share_memory_()

    def set_epoch(self, epoch: int) -> None:
        self.epoch.fill_(int(epoch))

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        import random

        from PIL import Image

        row = self.rows[index]
        with Image.open(row.path) as opened:
            opened.load()
            image = opened.convert("RGB")
        if self.augment:
            drawn = self.transform(image, random.Random(f"{row.name}:{int(self.epoch)}"))
        else:
            drawn = self.transform(image)
        return drawn, row.score, index, self.groups[index]


def decoded_stopping(units: list[Unit], transform, corpus: str, seed, log=say):
    """The eval rows, decoded and normalized ONCE and kept as fp16 beside the band.

    The deploy transform is deterministic and identical for every run, so decoding
    the stopping slice afresh every epoch of every run is one JPEG opened five
    hundred times over a band.

    ⚠ **Decoded serially and never through a loader.** A `DataLoader` draws its
    base seed off the global generator the moment an iterator is made, so a
    build-the-cache branch that used one would consume RNG that the read-the-cache
    branch does not — and two runs of one seed would part depending on whether the
    cache happened to be there. Five hundred pictures is six seconds.
    """
    import torch
    from PIL import Image

    cache = root() / f"decoded_stopping_{qualified(str(seed), corpus)}.pt"
    keys = [unit.key for unit in units]
    if cache.is_file():
        stored = torch.load(cache, map_location="cpu", weights_only=False)
        if stored["keys"] == keys:
            return stored["pictures"]
    began = time.time()
    out = None
    for index, unit in enumerate(units):
        with Image.open(unit.path) as opened:
            opened.load()
            picture = transform(opened.convert("RGB"))
        if out is None:
            out = torch.zeros((len(units), *picture.shape), dtype=torch.float16)
        out[index] = picture.to(torch.float16)
    cache.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"keys": keys, "pictures": out}, cache)
    log(f"[{HEAD}] decoded {len(units)} stopping picture(s) in {time.time() - began:.0f}s")
    return out


def _logits_of(model, pictures, recipe: dict, where: str, classes: int):
    """Every decoded row through the model, **offsets off**, in the order given."""
    import numpy
    import torch

    model.eval()
    size = int(recipe["batch_size"]) * 4
    out = numpy.zeros((len(pictures), classes - 1), dtype=numpy.float64)
    with torch.no_grad():
        for start in range(0, len(pictures), size):
            block = pictures[start : start + size].to(where, non_blocking=True).float()
            out[start : start + size] = model(block).float().cpu().numpy()
    return out


# --------------------------------------------------------------------------- #
# The fit.
# --------------------------------------------------------------------------- #
def fit(
    arm: str,
    seed: int = 0,
    band: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
    device: str = "auto",
    epochs: int | None = None,
    workers: int | None = None,
    log=say,
) -> dict:
    """Fit one arm at one seed under one band's stopping rule, and write its records.

    Resumable the way every trainer here is: an atomic snapshot an epoch, so a
    kill costs one epoch rather than the run, and a clean finish deletes it.

    **The rule is settled before the loop, not inside it.** If the stopping slice
    does not carry both classes at this band's boundary the run is launched under
    [`FIRST_BAND`]'s rule instead and its record says so — which is the honest
    shape of a fallback, as against a per-epoch branch that cannot fire.

    **Every recipe but [`FIRST_RECIPE`] has its own body**, and that is deliberate
    rather than a refusal to generalise: a recipe is reproducible only if it
    consumes the random stream in the order it consumed it the day it was fitted,
    and a shared loop with four branches in it is a loop whose stream moves the
    next time somebody adds a fifth.
    """
    if check_recipe(recipe) != FIRST_RECIPE:
        return _fit_drop_high_asymmetric(
            arm=arm,
            seed=seed,
            band=band,
            corpus=corpus,
            recipe=recipe,
            device=device,
            epochs=epochs,
            workers=workers,
            log=log,
        )

    import numpy
    import torch

    from fractal_wallpapers.models import finished_train, metrics, train

    # Held aside before `recipe` is rebound to the carried dict three lines into
    # this body: the parameter is a NAME and the local is the shipped judge's keys.
    recipe_name = check_recipe(recipe)

    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")
    if str(band) not in RULES:
        raise GradeTrainingError(f"{band!r} is not a band; the two are {sorted(RULES)}")
    check_corpus(corpus)

    state, shipped = initial_state()
    recipe = recipe_from(shipped)
    recipe["seed"] = int(seed)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if workers is not None:
        recipe["workers"] = int(workers)
    classes = int(recipe["classes"])

    units = read_population(corpus)
    split = apply_split(units, corpus=corpus)
    training = [unit for unit in units if unit.side == "train"]
    stopping = [unit for unit in units if unit.side == "stopping"]
    if not stopping:
        raise GradeTrainingError("the stopping slice is empty; there is nothing to stop on")

    # The one pre-flight branch, asked once and written into the record.
    wanted, tier = str(band), int(RULES[str(band)]["tier"])
    grades = [unit.score for unit in stopping]
    rule_record = {
        "asked_for": wanted,
        "boundary": tier,
        "stopping_slice_at_boundary": {
            "at_or_above": sum(1 for grade in grades if grade >= tier),
            "below": sum(1 for grade in grades if grade < tier),
        },
        "readable": readable_at(grades, tier),
    }
    if not rule_record["readable"]:
        wanted = FIRST_BAND
        rule_record["ran_under"] = wanted
        rule_record["says"] = (
            f"the stopping slice holds one class at >={tier}, so that boundary has no rank "
            f"statistic. This run was launched under {FIRST_BAND!r} instead, and its numbers "
            f"are not comparable with a run that stopped on the band's own rule"
        )
        log(f"[{HEAD}] ⚠ slice unreadable at >={tier}; running under {FIRST_BAND!r}")
    else:
        rule_record["ran_under"] = wanted
        rule_record["says"] = RULES[wanted]["says"]

    where = train.device_of(device)
    train.set_seed(int(recipe["seed"]))
    log(
        f"[{HEAD}] device {where}  torch {torch.__version__}  arm {arm}  seed {recipe['seed']}  "
        f"band {band} on {wanted}  "
        f"train {len(training)} {finished_train.histogram(training)}  "
        f"stopping {len(stopping)} {finished_train.histogram(stopping)}"
    )

    model = head.build(
        num_classes=classes,
        backbone=recipe["backbone"],
        pretrained=False,
        drop_rate=recipe["drop_rate"],
        drop_path_rate=recipe["drop_path_rate"],
    )
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        named = (list(missing) + list(unexpected))[:3]
        raise GradeTrainingError(
            f"the shipped judge's weights do not fit this architecture: {len(missing)} missing "
            f"and {len(unexpected)} unexpected tensors (e.g. {named}). Same architecture is "
            f"the premise of this head, not an aspiration."
        )
    model = model.to(where)
    freezing = freeze(model, arm)
    log(
        f"[{HEAD}] arm {arm}: {freezing['trainable_parameters']:,} of "
        f"{freezing['total_parameters']:,} parameters train "
        f"({freezing['trainable_share']:.1%}) — {freezing['says']}"
    )

    data_config = head.data_config(model)
    head_parameters = [p for p in model.get_classifier().parameters() if p.requires_grad]
    head_ids = {id(parameter) for parameter in head_parameters}
    backbone_parameters = [
        p for p in model.parameters() if p.requires_grad and id(p) not in head_ids
    ]
    groups = [{"params": head_parameters, "lr": recipe["head_lr"]}]
    if backbone_parameters:
        groups.insert(0, {"params": backbone_parameters, "lr": recipe["backbone_lr"]})
    optimizer = torch.optim.AdamW(groups, weight_decay=recipe["weight_decay"])
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=recipe["epochs"])

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
    examples, loader, mass = _loader(training, train_transform, recipe, where)

    stopping_paths = [unit.path for unit in stopping]
    stopping_labels = numpy.array([unit.score for unit in stopping])
    stopping_batches = numpy.array([unit.batch for unit in stopping])
    cutpoint = min(int(recipe["selection_cutpoint"]), classes) - 2

    directory = run_dir(arm, seed, band, corpus, recipe_name)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        lock = train.claim(directory)
    except RuntimeError as taken:
        raise GradeTrainingError(str(taken)) from None
    resume = directory / "resume.pt"

    best_metric, best_state, best_epoch, best_rule, history = float("inf"), None, -1, "", []
    segments, start = [], 0
    if resume.is_file():
        saved = torch.load(resume, map_location="cpu", weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        schedule.load_state_dict(saved["schedule"])
        best_metric, best_epoch = saved["best_metric"], saved["best_epoch"]
        best_state, history = saved["best_state"], saved["history"]
        best_rule = saved.get("best_rule", "")
        segments = list(saved.get("segments") or [])
        start = saved["epoch"] + 1
        torch.set_rng_state(saved["torch_rng"].cpu().to(torch.uint8))
        if where == "cuda" and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(
                [state_.cpu().to(torch.uint8) for state_ in saved["cuda_rng"]]
            )
        numpy.random.set_state(saved["numpy_rng"])
        log(f"[{HEAD}] resumed at epoch {start} (best {best_metric:.4f} at epoch {best_epoch})")

    began = time.time()
    stopped_early: dict | None = None

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

    for epoch in range(start, int(recipe["epochs"])):
        examples.set_epoch(epoch)
        set_train_mode(model, arm)
        clock, running, seen = time.time(), 0.0, 0
        for crops, labels, _index in loader:
            crops = crops.to(where, non_blocking=True)
            labels = labels.to(where)
            optimizer.zero_grad(set_to_none=True)
            loss = head.loss_of(model(crops), labels, num_classes=classes)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], recipe["grad_clip"]
            )
            optimizer.step()
            running += loss.item() * crops.size(0)
            seen += crops.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise GradeTrainingError(f"the head went non-finite at epoch {epoch}")

        probabilities = train.score(model, stopping_paths, deploy_transform, where, classes, recipe)
        value, rule = objective(stopping_labels, probabilities, wanted)
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "selection_loss": value,
            "selection_rule": rule,
            f"stopping_ap_ge{cutpoint + 2}": metrics.average_precision(
                (stopping_labels >= cutpoint + 2).astype(int), probabilities[:, cutpoint]
            ),
        }
        for index in range(classes - 1):
            record[f"stopping_auc_ge{index + 2}"] = metrics.auc(
                (stopping_labels >= index + 2).astype(int), probabilities[:, index]
            )
            record[f"stopping_mean_p_ge{index + 2}"] = float(probabilities[:, index].mean())
        record["stopping_spearman"] = metrics.spearman(
            stopping_labels, head.rank_score(probabilities)
        )
        # Per batch, reported and never selected on: the epoch is chosen on the
        # pooled slice, and these three columns are how a reader sees whether the
        # stratification bought anything.
        for name in sorted(set(stopping_batches.tolist())):
            mask = stopping_batches == name
            if mask.any():
                record[f"stopping_ap_ge{cutpoint + 2}_{name}"] = metrics.average_precision(
                    (stopping_labels[mask] >= cutpoint + 2).astype(int),
                    probabilities[mask, cutpoint],
                )
        history.append(record)
        log(
            f"[{HEAD}] epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"AP>={cutpoint + 2} {train.shown(record[f'stopping_ap_ge{cutpoint + 2}'])}  "
            + "  ".join(
                f"AUC>={index + 2} {train.shown(record[f'stopping_auc_ge{index + 2}'])}"
                for index in range(classes - 1)
            )
            + f"  rho {train.shown(record['stopping_spearman'])}  ({record['seconds']}s)"
        )

        if value < best_metric:
            best_metric, best_epoch, best_rule = value, epoch, rule
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
                "best_rule": best_rule,
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

        if epoch - best_epoch >= int(recipe["patience"]):
            stopped_early = {
                "at_epoch": epoch,
                "of_epochs": int(recipe["epochs"]),
                "patience": int(recipe["patience"]),
                "best_epoch": best_epoch,
            }
            log(
                f"[{HEAD}] stopping at epoch {epoch}: no improvement in "
                f"{recipe['patience']} epochs (best {best_epoch})"
            )
            break

    lock.unlink(missing_ok=True)
    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed, band, corpus, recipe_name),
        "arm": arm,
        "band": str(band),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": recipe_name,
        "recipe_is": RECIPES[recipe_name]["says"],
        **recipe,
        "initialised_from": {
            "artifact": str(SOURCE).replace("\\", "/"),
            "run": shipped.get("run"),
            "tag": "weights-v6",
            "says": "a COPY. Never a shared trunk — a moved trunk is a judge flip",
        },
        "freezing": freezing,
        "stopping_rule": rule_record,
        "stopped_early": stopped_early,
        "best_epoch": best_epoch,
        "best_selection_rule": best_rule,
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "inherited": INHERITANCE,
        # The split's shape and never its per-row arrays: this file is tracked,
        # and three thousand entries naming every row would be a record nobody
        # reads carried in git forever. The arrays live in `split.json`, under
        # the regenerable tree, which is where the fit reads them from.
        "split": {key: value for key, value in split.items() if not key.endswith("_of_row")},
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, directory / "best.pt")
    torch.save({"state_dict": last_state, "config": config}, directory / "last.pt")
    if resume.is_file():
        resume.unlink()

    # The chosen epoch's own read of the stopping slice, one row at a time with
    # its whole join — so the band's table can be rebuilt without the GPU.
    model.load_state_dict({key: value.to(where) for key, value in best_state.items()})
    chosen = train.score(model, stopping_paths, deploy_transform, where, classes, recipe)
    _write_scores(directory, arm, seed, band, corpus, recipe_name, stopping, chosen, classes)

    read = _read_of(stopping_labels, chosen, cutpoint, classes)
    # The same read on the rows the two INCUMBENTS can be read on, so that a bar
    # stated against them compares like with like. A row drawn from outside the
    # seating pool carries no candidate reading at all, and on the corrected
    # corpus that is a hundred `low_anchor` rows: comparing an arm's AUC over the
    # whole slice against a column's over four fifths of it would be two
    # populations wearing one number.
    on_gate = [index for index, unit in enumerate(stopping) if unit.candidate_p_ge4 is not None]
    gate_read = (
        _read_of(stopping_labels[on_gate], chosen[on_gate], cutpoint, classes)
        if len(on_gate) not in (0, len(stopping))
        else dict(read)
    )
    gate_read["of"] = len(stopping)
    gate_read["is"] = (
        "the stopping rows the shipped judge read as candidates — the slice both "
        "incumbents are readable on, and the slice a bar is stated over"
    )
    record = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed, band, corpus, recipe_name),
        "arm": arm,
        "band": str(band),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": recipe_name,
        "seed": int(seed),
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "segments": launched(history[-1]["epoch"] if history else int(recipe["epochs"]) - 1),
        "best_epoch": best_epoch,
        "best_selection_objective": best_metric,
        "best_selection_rule": best_rule,
        "stopped_early": stopped_early,
        "selection_metric": (
            f"{RULES[wanted]['says']}, maximized (recorded negated, because the loop minimizes)"
        ),
        "stopping_rule": rule_record,
        "freezing": freezing,
        "held_out": read,
        "held_out_on_the_gate_column": gate_read,
        "held_out_is": (
            "the stopping slice. It is the shipped recipe's only holdout and the epoch was "
            "chosen on it, so every number here is optimistic by one early stop, and the "
            "store is not eval-eligible — this is a within-store reading and nothing more"
        ),
        "pictures": {"train": len(training), "stopping": len(stopping), "total": len(units)},
        "class_counts": {
            "train": finished_train.histogram(training),
            "stopping": finished_train.histogram(stopping),
        },
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


def _fit_drop_high_asymmetric(
    arm: str,
    seed: int,
    band: str,
    corpus: str,
    recipe: str,
    device: str = "auto",
    epochs: int | None = None,
    workers: int | None = None,
    log=say,
) -> dict:
    """[`RECIPES`]`['drop_high_asymmetric']`, fitted once. The adopted column's own.

    A faithful port of the recipe `best_head_20260910` measured and
    `deterministic_refit_20260910` fitted the shipped heads under, and *faithful*
    is the operative word: every line that touches the random stream is in the
    order it was in that day, because the promise this recipe carries is that its
    checkpoints rebuild from their seeds.

    **No resume and no early stop.** The horizon is fixed and the patience sits
    above it, so there is no stopping test to fire and the AUC(>=4) checkpoint is
    free to land anywhere on the curve. A resume would have to restore the loader's
    position in the random stream as well as the model's weights, and a run is
    three minutes.
    """
    import numpy
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    from fractal_wallpapers.models import finished_train, metrics, train

    knobs = RECIPES[check_recipe(recipe)]
    if arm not in knobs["arms"]:
        raise GradeTrainingError(
            f"{recipe!r} runs {list(knobs['arms'])} and not {arm!r} — the others were "
            f"measured and dropped, and re-fitting one would buy a row saying so"
        )
    if str(band) not in RULES:
        raise GradeTrainingError(f"{band!r} is not a band; the two are {sorted(RULES)}")
    check_corpus(corpus)
    assert_symmetric_case()
    train.make_deterministic()

    state, shipped = initial_state()
    carried = recipe_from(shipped)
    carried["seed"] = int(seed)
    carried["epochs"] = int(knobs["epochs"] if epochs is None else epochs)
    carried["patience"] = int(knobs["patience"])
    carried["drop_rate"] = float(knobs["drop_rate"])
    carried["drop_path_rate"] = float(knobs["drop_path_rate"])
    carried["workers"] = int(knobs["workers"] if workers is None else workers)
    classes = int(carried["classes"])

    units = read_population(corpus)
    split = apply_split(units, corpus=corpus)
    training = [unit for unit in units if unit.side == "train"]
    stopping = [unit for unit in units if unit.side == "stopping"]
    if not stopping:
        raise GradeTrainingError("the stopping slice is empty; there is nothing to stop on")
    sittings = sorted({str(unit.batch) for unit in units})
    index_of = {name: position for position, name in enumerate(sittings)}
    groups = [index_of[str(unit.batch)] for unit in training]

    tier = int(RULES[str(band)]["tier"])
    grades = [unit.score for unit in stopping]
    rule_record = {
        "asked_for": str(band),
        "boundary": tier,
        "stopping_slice_at_boundary": {
            "at_or_above": sum(1 for grade in grades if grade >= tier),
            "below": sum(1 for grade in grades if grade < tier),
        },
        "readable": readable_at(grades, tier),
        "ran_under": str(band),
        "says": RULES[str(band)]["says"],
    }
    if not rule_record["readable"]:
        raise GradeTrainingError(
            f"the stopping slice holds one class at >={tier}, and this recipe checkpoints on "
            f"that boundary and nothing else — there is no rule to fall back to"
        )

    where = train.device_of(device)
    train.set_seed(int(carried["seed"]))

    model = head.build(
        num_classes=classes,
        backbone=carried["backbone"],
        pretrained=False,
        drop_rate=carried["drop_rate"],
        drop_path_rate=carried["drop_path_rate"],
    )
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        raise GradeTrainingError(
            f"the shipped judge's weights do not fit this architecture: {len(missing)} "
            f"missing and {len(unexpected)} unexpected tensors"
        )
    model = model.to(where)
    freezing = freeze(model, arm)

    data_config = head.data_config(model)
    target_dims = tuple(carried["target_dims"])
    train_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=True,
        border_crop=carried["border_crop"],
        jpeg=None,
        brightness=0.0,
        contrast=0.0,
        target=target_dims,
    )
    deploy_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=False,
        target=target_dims,
    )

    head_parameters = [p for p in model.get_classifier().parameters() if p.requires_grad]
    head_ids = {id(parameter) for parameter in head_parameters}
    backbone_parameters = [
        p for p in model.parameters() if p.requires_grad and id(p) not in head_ids
    ]
    parameter_groups = [{"params": head_parameters, "lr": carried["head_lr"]}]
    if backbone_parameters:
        parameter_groups.insert(0, {"params": backbone_parameters, "lr": carried["backbone_lr"]})
    # A learned scalar per sitting, zero-initialised, **centred at every use** so
    # the parameterization is identified — the classifier's own bias can absorb
    # any constant, and an uncentred vector would wander with it. Its own group at
    # ten times the head's rate and no decay: a handful of scalars have about a
    # tier to travel inside thirty epochs.
    offsets = torch.nn.Parameter(torch.zeros(len(sittings), device=where))
    parameter_groups.append(
        {"params": [offsets], "lr": carried["head_lr"] * 10, "weight_decay": 0.0}
    )
    optimizer = torch.optim.AdamW(parameter_groups, weight_decay=carried["weight_decay"])
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=carried["epochs"])

    raw, mass = finished_train.weights(training)
    sampler = WeightedRandomSampler(
        torch.tensor(raw, dtype=torch.double), num_samples=len(training), replacement=True
    )
    examples = SittingPictures(training, train_transform, groups, True)
    loader = DataLoader(
        examples,
        batch_size=carried["batch_size"],
        sampler=sampler,
        num_workers=carried["workers"],
        pin_memory=(where == "cuda"),
        persistent_workers=bool(carried["workers"]),
        prefetch_factor=4 if carried["workers"] else None,
        drop_last=False,
    )

    stopping_labels = numpy.array([unit.score for unit in stopping])
    ranks_stopping = stopping_labels - 1
    stopping_pictures = decoded_stopping(
        stopping, deploy_transform, corpus, split.get("split_seed", SPLIT_SEED), log=log
    )
    cutpoint = min(int(carried["selection_cutpoint"]), classes) - 2

    directory = run_dir(arm, seed, band, corpus, recipe)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        lock = train.claim(directory)
    except RuntimeError as taken:
        raise GradeTrainingError(str(taken)) from None
    log(
        f"[{HEAD}] device {where}  arm {arm}  seed {seed}  recipe {recipe}  "
        f"train {len(training)} {finished_train.histogram(training)}  "
        f"stopping {len(stopping)} {finished_train.histogram(stopping)}  "
        f"offsets over {len(sittings)} sitting(s)"
    )

    history: list[dict] = []
    best_auc, best_state, best_epoch = -float("inf"), None, -1
    began = time.time()

    for epoch in range(int(carried["epochs"])):
        examples.set_epoch(epoch)
        set_train_mode(model, arm)
        clock, running, seen = time.time(), 0.0, 0
        for crops, labels, _index, group in loader:
            crops = crops.to(where, non_blocking=True)
            labels = labels.to(where)
            optimizer.zero_grad(set_to_none=True)
            centred = offsets - offsets.mean()
            read = model(crops) + centred[group.to(where)].unsqueeze(1)
            loss = weighted_corn_loss(
                read.float(), (labels - 1).long(), classes, float(knobs["neg_weight"])
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], carried["grad_clip"]
            )
            optimizer.step()
            running += loss.item() * crops.size(0)
            seen += crops.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise GradeTrainingError(f"the head went non-finite at epoch {epoch}")

        held = _logits_of(model, stopping_pictures, carried, where, classes)
        probabilities = head.probabilities(held)
        with torch.no_grad():
            shown = (offsets - offsets.mean()).detach().cpu().numpy().tolist()
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "eval_loss": unweighted_corn_loss(held, ranks_stopping, classes - 1),
            "offsets": {name: round(value, 4) for name, value in zip(sittings, shown, strict=True)},
            f"stopping_ap_ge{cutpoint + 2}": metrics.average_precision(
                (stopping_labels >= cutpoint + 2).astype(int), probabilities[:, cutpoint]
            ),
        }
        for index in range(classes - 1):
            record[f"stopping_auc_ge{index + 2}"] = metrics.auc(
                (stopping_labels >= index + 2).astype(int), probabilities[:, index]
            )
        record["stopping_spearman"] = metrics.spearman(
            stopping_labels, head.rank_score(probabilities)
        )
        value, rule = objective(stopping_labels, probabilities, str(band))
        record["selection_loss"] = value
        record["selection_rule"] = rule
        history.append(record)
        log(
            f"[{HEAD}] epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"eval {record['eval_loss']:.4f}  "
            f"AUC>=4 {train.shown(record[f'stopping_auc_ge{classes}'])}  "
            f"({record['seconds']}s)"
        )

        auc = record[f"stopping_auc_ge{tier}"]
        if auc is not None and auc > best_auc:
            best_auc, best_epoch = auc, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    lock.unlink(missing_ok=True)
    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed, band, corpus, recipe),
        "arm": arm,
        "band": str(band),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": check_recipe(recipe),
        "recipe_is": knobs["says"],
        **carried,
        "neg_weight": float(knobs["neg_weight"]),
        "offset": knobs["offset"],
        "offset_groups": sittings,
        "offset_is": (
            "a learned scalar per sitting, centred at every use and DROPPED at inference — "
            "the column a seating reads is the model without it, which is the average "
            "sitting's scale"
        ),
        "checkpoint_rule": knobs["checkpoint"],
        "determinism": train.determinism_record(),
        "initialised_from": {
            "artifact": str(SOURCE).replace("\\", "/"),
            "run": shipped.get("run"),
            "tag": "weights-v6",
            "says": "a COPY. Never a shared trunk — a moved trunk is a judge flip",
        },
        "freezing": freezing,
        "stopping_rule": rule_record,
        "stopped_early": None,
        "best_epoch": best_epoch,
        "best_selection_rule": str(band),
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "inherited": INHERITANCE,
        "split": {key: value for key, value in split.items() if not key.endswith("_of_row")},
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, directory / "best.pt")
    torch.save({"state_dict": last_state, "config": config}, directory / "last.pt")

    model.load_state_dict({key: value.to(where) for key, value in best_state.items()})
    chosen = head.probabilities(_logits_of(model, stopping_pictures, carried, where, classes))
    _write_scores(directory, arm, seed, band, corpus, recipe, stopping, chosen, classes)

    read = _read_of(stopping_labels, chosen, cutpoint, classes)
    on_gate = [index for index, unit in enumerate(stopping) if unit.candidate_p_ge4 is not None]
    gate_read = (
        _read_of(stopping_labels[on_gate], chosen[on_gate], cutpoint, classes)
        if len(on_gate) not in (0, len(stopping))
        else dict(read)
    )
    gate_read["of"] = len(stopping)
    gate_read["is"] = (
        "the stopping rows the shipped judge read as candidates — the slice both "
        "incumbents are readable on, and the slice a bar is stated over"
    )
    record = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed, band, corpus, recipe),
        "arm": arm,
        "band": str(band),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": check_recipe(recipe),
        "seed": int(seed),
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "segments": [
            {
                "from_epoch": 0,
                "through_epoch": int(carried["epochs"]) - 1,
                "wall_seconds": round(time.time() - began, 1),
            }
        ],
        "best_epoch": best_epoch,
        "best_selection_objective": -float(best_auc),
        "best_selection_rule": str(band),
        "stopped_early": None,
        "selection_metric": (
            f"{RULES[str(band)]['says']}, maximized (recorded negated, because the loop "
            f"minimizes). No early stop: the horizon is fixed and the patience sits above it"
        ),
        "stopping_rule": rule_record,
        "freezing": freezing,
        "held_out": read,
        "held_out_on_the_gate_column": gate_read,
        "held_out_is": (
            "the stopping slice. It is the shipped recipe's only holdout and the epoch was "
            "chosen on it, so every number here is optimistic by one choice, and the store "
            "is not eval-eligible — this is a within-store reading and nothing more"
        ),
        "pictures": {"train": len(training), "stopping": len(stopping), "total": len(units)},
        "class_counts": {
            "train": finished_train.histogram(training),
            "stopping": finished_train.histogram(stopping),
        },
        "sampled_mass": mass,
        "history": history,
        "checkpoints": {
            "best": tracked_name(directory / "best.pt"),
            "last": tracked_name(directory / "last.pt"),
        },
    }
    (directory / "config.json").write_text(
        json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    (directory / "metrics.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    log(f"[{HEAD}] {record['run']} done in {record['wall_seconds']}s, AUC epoch {best_epoch}")
    return record


def fit_band(
    arms=None,
    seeds=SEEDS,
    band_name: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
    device: str = "auto",
    log=say,
    **rest,
) -> dict:
    """Fit every run of the grid that is not already on disk, **one at a time**.

    Sequential and not a knob, for `models/render/README.md`'s reason: this box's
    commit charge cannot afford two trainers, and the failure it produces —
    `[WinError 1455] The paging file is too small`, out of a CUDA DLL load — looks
    like a machine fault rather than like scheduling.

    A run whose `metrics.json` is already there is skipped rather than re-fitted,
    so a killed band is resumed by re-launching it.
    """
    arms = tuple(arms if arms is not None else RECIPES[check_recipe(recipe)]["arms"])
    done, ran = [], []
    for arm in arms:
        for seed in seeds:
            named = run_name(arm, seed, band_name, corpus, recipe)
            if (run_dir(arm, seed, band_name, corpus, recipe) / "metrics.json").is_file():
                done.append(named)
                log(f"[{HEAD}] {named} is already fitted — skipping")
                continue
            record = fit(
                arm=arm,
                seed=seed,
                band=band_name,
                corpus=corpus,
                recipe=recipe,
                device=device,
                log=log,
                **rest,
            )
            ran.append(record["run"])
    return {
        "fitted": ran,
        "already_there": done,
        "band": band(arms, seeds, band_name, corpus, recipe),
    }


def _read_of(labels, probabilities, cutpoint: int, classes: int) -> dict:
    """Every boundary's AP and AUC over one slice, plus the order statistic."""
    import numpy

    from fractal_wallpapers.models import metrics

    out: dict = {"rows": int(len(labels))}
    for index in range(classes - 1):
        hits = (numpy.asarray(labels) >= index + 2).astype(int)
        out[f"ap_ge{index + 2}"] = metrics.average_precision(hits, probabilities[:, index])
        out[f"auc_ge{index + 2}"] = metrics.auc(hits, probabilities[:, index])
    out["spearman"] = metrics.spearman(labels, head.rank_score(probabilities))
    out["cutpoint"] = cutpoint + 2
    return out


def _write_scores(
    directory: Path,
    arm: str,
    seed: int,
    band: str,
    corpus: str,
    recipe: str,
    units,
    probabilities,
    classes: int,
) -> None:
    """The chosen epoch's read of the stopping slice, a row carrying its join."""
    import numpy

    path = directory / "scores.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for unit, probability in zip(units, probabilities, strict=True):
            row = {
                "schema": SCHEMA,
                "head": HEAD,
                "run": run_name(arm, seed, band, corpus, recipe),
                "key": unit.key,
                "grade": unit.score,
                "batch": unit.batch,
                "block": unit.block,
                "sheet": unit.sheet,
                "place": unit.place,
                "partition": unit.partition,
                "mode": unit.mode,
                "leveled": unit.leveled,
                "seated": unit.seated,
                "judge_label_p_ge4": unit.label_p_ge4,
                "judge_candidate_p_ge4": unit.candidate_p_ge4,
            }
            for index in range(classes - 1):
                row[f"p_ge{index + 2}"] = float(probability[index])
            row["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_run(
    arm: str, seed: int, band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE
) -> dict:
    path = run_dir(arm, seed, band, corpus, recipe) / "metrics.json"
    if not path.is_file():
        raise GradeTrainingError(f"{path} is not there — that run has not been fitted")
    return json.loads(path.read_text(encoding="utf-8"))


def baselines(corpus: str = CORPUS) -> dict:
    """The shipped judge's own columns over the stopping slice, at both geometries.

    **Recomputed on this band's own rows rather than quoted from anywhere.** The
    numbers on the store's README are over all thousand rows; these are over the
    two hundred the arms are read on, and a table that mixed the two would be
    comparing an arm against a different population's baseline.

    `candidate_p_ge4` is the one a seating actually walks and is therefore the
    number to beat. `label_p_ge4` is the same judge on the picture the verdict was
    cast on, and it is here because it is the *easier* baseline — it reads the
    exact pixels the person saw — so an arm that fails to beat it has not merely
    lost to the deployment column.
    """
    import numpy

    from fractal_wallpapers.models import metrics

    units = read_population(corpus)
    apply_split(units, corpus=corpus)
    stopping = [unit for unit in units if unit.side == "stopping"]
    labels = numpy.array([unit.score for unit in stopping])
    out: dict = {"corpus": check_corpus(corpus), "rows": len(stopping), "base_rates": {}}
    for boundary in (2, 3, 4):
        out["base_rates"][f"ge{boundary}"] = round(float((labels >= boundary).mean()), 4)
    out["gate_column_rows"] = sum(1 for unit in stopping if unit.candidate_p_ge4 is not None)
    out["gate_column_is"] = (
        "the rows the shipped judge read AS CANDIDATES. A row drawn from somewhere other "
        "than the seating pool carries no such reading — the correction sitting's 100 "
        "`low_anchor` rows are coarse-3 verdicts about 1280x720 pictures and were never "
        "candidates — so the two incumbents are readable on this slice and not on the whole "
        "stopping side"
    )
    for column in ("candidate_p_ge3", "candidate_p_ge4", "label_p_ge3", "label_p_ge4"):
        values = [getattr(unit, column) for unit in stopping]
        kept = [index for index, value in enumerate(values) if value is not None]
        if not kept:
            out[column] = {"rows_carrying_it": 0, "of": len(stopping), "read": None}
            continue
        # Dropped and counted, never imputed — [`_rank_key_baseline`]'s rule, which
        # this branch used to refuse instead. A column absent on a fifth of the
        # slice is a column read on the other four fifths and SAID to be, where
        # refusing outright makes a bar unstatable for want of rows nobody
        # claimed it covered.
        scores = numpy.array([values[index] for index in kept], dtype=float)
        mine = numpy.asarray(labels)[kept]
        read: dict = {"rows_carrying_it": len(scores), "of": len(stopping)}
        for boundary in (2, 3, 4):
            hits = (mine >= boundary).astype(int)
            read[f"ap_ge{boundary}"] = metrics.average_precision(hits, scores)
            read[f"auc_ge{boundary}"] = metrics.auc(hits, scores)
        read["spearman"] = metrics.spearman(mine, scores)
        out[column] = read
    out["rank_key"] = _rank_key_baseline(stopping, labels)
    return out


def _rank_key_baseline(stopping, labels) -> dict:
    """The **shipped seating key** over the same rows — the second incumbent.

    `curation.rank_key` is what a seating ranks on today, and `p_ge4` is only one
    of its four columns. A head that beat the judge's column and lost to the key
    would have improved nothing anybody ships, which is the correction
    [`curation.render_grade`] made for the render judge and the same one applies
    here.

    The columns are read off the stores the key itself reads — the location
    scores, the flatness sidecar — so this opens no picture and re-fits nothing.
    A row missing either is **left out and counted**, never imputed: the key
    refuses a candidate it cannot read and so does this.
    """
    import numpy

    from fractal_wallpapers.models import metrics

    try:
        from fractal_wallpapers.curation import flatness, intake, rank_key

        key = rank_key.load()
        locations = intake.read_scores()
        flat = flatness.by_recipe()
    except Exception as unreadable:  # noqa: BLE001 — the reason belongs on the record
        return {"unreadable": f"{type(unreadable).__name__}: {unreadable}"}

    values, kept, gaps = [], [], {"no_flatness": 0, "no_location_reading": 0, "no_column": 0}
    for index, unit in enumerate(stopping):
        reading = flat.get(unit.key)
        if reading is None:
            gaps["no_flatness"] += 1
            continue
        place = locations.get(unit.location) or {}
        loc = place.get("p_ge4")
        if loc is None:
            gaps["no_location_reading"] += 1
        if unit.candidate_p_ge3 is None or unit.candidate_p_ge4 is None:
            gaps["no_column"] += 1
            continue
        try:
            values.append(
                key.score(
                    {
                        "loc_p_ge4": rank_key.NO_LOCATION_READING if loc is None else float(loc),
                        "p_ge3": float(unit.candidate_p_ge3),
                        "p_ge4": float(unit.candidate_p_ge4),
                        flatness.COLUMN: float(reading),
                    }
                )
            )
        except rank_key.RankKeyError:
            gaps["no_column"] += 1
            continue
        kept.append(index)
    if not kept:
        return {"unreadable": "no row of the stopping slice carries every column", **gaps}

    mine = numpy.asarray(labels)[kept]
    scores = numpy.array(values, dtype=float)
    read: dict = {"rows_carrying_it": len(scores), "of": len(stopping), **gaps}
    for boundary in (2, 3, 4):
        hits = (mine >= boundary).astype(int)
        read[f"ap_ge{boundary}"] = metrics.average_precision(hits, scores)
        read[f"auc_ge{boundary}"] = metrics.auc(hits, scores)
    read["spearman"] = metrics.spearman(mine, scores)
    read["fitted_at"] = key.document.get("fitted_at")
    read["rows_it_is_read_on"] = (
        "only the stopping rows the key can read, so an arm compared against it is compared "
        "on those rows and not on all of them"
    )
    return read


# --------------------------------------------------------------------------- #
# Reading a pool through the picked run.
# --------------------------------------------------------------------------- #
def pool_scores_path() -> Path:
    """Where this head's read of the seating pool lands.

    **The one spelling of this path.** `curation.solve` reads it to resolve the
    cascade order and reaches it through this function rather than building it
    from a root and a string, so a move here moves both.
    """
    return root() / "pool_scores.jsonl"


def superseded_pool_scores_path(run: str) -> Path:
    """Where the scores a re-score is about to replace are kept.

    Named for the **run that wrote them**, which is the only thing that makes
    them interpretable: a row's `p_ge4` means nothing without the head it came
    out of, and two heads' columns are not on one scale — the refit reads 9.6%
    of the pool above 0.50 where the shipped head reads 27.8%.

    A second archive of one run gets a stamp rather than overwriting the first.
    The first is the file the records taken under it were made against, and
    losing it to a later, wider read of the same head would make those records
    unreproducible without anything looking broken.
    """
    where = root() / f"pool_scores_{run}.jsonl"
    if not where.is_file():
        return where
    # [`_stamp`]'s own spelling carries colons, which are not legal in a Windows
    # filename — the compact form is what every stamped name in this project
    # uses, and a path built from the readable one fails on this machine and
    # passes on CI.
    stamp = _stamp().replace("-", "").replace(":", "")
    return root() / f"pool_scores_{run}_{stamp}.jsonl"


def keep_superseded_pool_scores(log=say) -> Path | None:
    """Move the live pool scores aside, if there are any, and say where they went.

    ⚠ **[`pool_scores_path`] is one-shot and a re-score is destructive.** Every
    solve record ever taken resolves its cascade order out of that one file, so
    overwriting it makes every prior record's ordering unreproducible. This runs
    before the write, always, and it is not optional or flagged: an adoption that
    silently invalidated the records it was judged against would be the worst
    version of this act.

    The run name is read off the file's own first row rather than from a caller,
    so the archive cannot be misnamed by a caller that thinks it knows which head
    is live.
    """
    live = pool_scores_path()
    if not live.is_file():
        return None
    run = "unnamed"
    with live.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                run = str(json.loads(line).get("run") or "unnamed")
                break
    kept = superseded_pool_scores_path(run)
    live.replace(kept)
    log(f"[{HEAD}] kept the superseded scores of {run} at {kept}")
    return kept


def pool_scores_run(path: Path | None = None) -> str | None:
    """Which run wrote the live pool scores, or `None` if nothing has.

    **A `p_fine` value is meaningless without it.** The shipped head and the
    corrected refit put 27.8% and 9.6% of one pool above 0.50, so a record
    saying `fine_bar: 0.184` says nothing at all unless it also says whose
    column that 0.184 was read on. Cheap on purpose — one line, not the file —
    because a solve record builder asks it and the file is nine megabytes.
    """
    where = pool_scores_path() if path is None else Path(path)
    if not where.is_file():
        return None
    with where.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return str(json.loads(line).get("run") or "") or None
    return None


def read_pool_scores(path: Path | None = None) -> dict:
    """`{candidate key: {p_ge2, p_ge3, p_ge4, rank_score}}`, or `{}` if unread.

    Empty rather than raising, because the caller that matters is a seating
    resolving an order: a missing file means this head has not read this pool,
    which is a thing for the seating to refuse with its own message about its own
    key rather than a traceback out of a model module.
    """
    where = pool_scores_path() if path is None else Path(path)
    if not where.is_file():
        return {}
    out: dict = {}
    for line in where.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row["key"])] = row
    return out


def ensemble_name(
    arm: str, seeds, band: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE
) -> str:
    """[`run_name`]'s spelling for a column k checkpoints wrote, with `_kN` for `_seedN`.

    A column is meaningless without the head it came out of, and an ensemble's
    head is k of them — so the name says how many rather than naming one of the
    three and being wrong about the other two.
    """
    stem = f"{arm}_k{len(tuple(seeds))}"
    if str(band) != FIRST_BAND:
        stem = f"{band}_{stem}"
    if check_recipe(recipe) != FIRST_RECIPE:
        stem = f"{recipe}_{stem}"
    return qualified(stem, corpus)


def shipped_runs(
    band_name: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE, seeds=SEEDS
) -> tuple[str, list[int], str]:
    """`(arm, seeds, the name of the column they write)` — what this recipe ships.

    **The two recipes ship different things and the difference is one flag.**
    `inherited` ships the band's MEDIAN seed, because its epoch surface is flat
    enough that the best of three is a coin flip. `drop_high_asymmetric` ships
    **every** seed averaged on the probability scale, because
    `stability_and_sheet_20260910` measured churn falling as `0.108 + 0.657/sqrt(k)`
    with no knee — three averaged heads are more reproducible than re-running one.
    """
    read = band(seeds=seeds, band_name=band_name, corpus=corpus, recipe=recipe)
    winner = str(read["pick"]["arm"])
    if not RECIPES[check_recipe(recipe)]["ensemble"]:
        chosen = [int(read["pick"]["seed"])]
        return winner, chosen, run_name(winner, chosen[0], band_name, corpus, recipe)
    chosen = [int(row["seed"]) for row in read["runs"] if row["arm"] == winner]
    return winner, sorted(chosen), ensemble_name(winner, chosen, band_name, corpus, recipe)


def score_pool(
    candidates,
    arm: str | None = None,
    seed: int | None = None,
    band: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
    device: str = "auto",
    seeds=SEEDS,
    log=say,
):
    """Read a whole pool through one run's chosen checkpoint, and write the rows.

    `candidates` is whatever [`curation.solve.pool`] hands back — anything with a
    `key` and a `picture` — and this opens each of those pictures once. It is the
    only pass here that costs more than a minute, and it costs it in decode
    rather than in forward: the pictures are the ledger's own 640x360 JPEGs and
    nothing is re-rendered.

    ⚠ **The rows this writes are a cascade's SECOND stage and nothing else.** A
    reader that ranked the whole file would be ranking rows this head never saw
    the like of — every row it was fitted on had cleared the gate. `solve` applies
    it above the bar and only there.

    Which is why **only the above-bar rows are read**. It is not a saving so much
    as the same statement made twice: a score written for a row the cascade may
    not use is a number that exists only to be misread, and on this pool it would
    be seven rows in eight — 223,438 of 260,862 on 2026-09-06 — and twenty minutes
    of decode. A candidate that carries no `above_bar` is read, because a caller
    handing in its own list has not said the rows are pool rows.
    """
    import numpy

    from fractal_wallpapers.models import train
    from fractal_wallpapers.paths import Tiers, rehome

    if arm is None or seed is None:
        arm, chosen, column = shipped_runs(band, corpus, recipe, seeds)
    else:
        chosen, column = [int(seed)], run_name(arm, int(seed), band, corpus, recipe)
    checkpoints = [run_dir(arm, one, band, corpus, recipe) / "best.pt" for one in chosen]
    for checkpoint in checkpoints:
        if not checkpoint.is_file():
            raise GradeTrainingError(f"{checkpoint} is not there — that run has not been fitted")
    loaded = [load_checkpoint(checkpoint, device) for checkpoint in checkpoints]
    models = [one[0] for one in loaded]
    config, where = loaded[0][1], loaded[0][2]
    for _model, other, _where in loaded[1:]:
        differing = [
            key
            for key in ("classes", "backbone", "mean", "std", "interpolation", "target_dims")
            if other.get(key) != config.get(key)
        ]
        if differing:
            raise GradeTrainingError(
                f"the ensemble's checkpoints disagree about {differing} — a mean over two "
                f"different transforms is not a column"
            )

    tiers = Tiers.current()
    keys, paths, absent, below = [], [], 0, 0
    for candidate in candidates:
        if getattr(candidate, "above_bar", True) is False:
            below += 1
            continue
        named = getattr(candidate, "picture", None)
        resolved = None if not named else rehome(str(named), tiers)
        if resolved is None or not resolved.is_file():
            absent += 1
            continue
        keys.append(str(candidate.key))
        paths.append(resolved)
    if not paths:
        raise GradeTrainingError("no candidate of this pool has a picture on disk to read")

    storage.require_hot(*{path.parent for path in paths}, what="reading a pool through this head")
    began = time.time()
    log(f"[{HEAD}] reading {len(paths):,} pictures through {column} ({len(models)} head(s))")
    classes = int(config["classes"])
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    # **Averaged on the PROBABILITY scale**, which is the scale the pool carries,
    # the bar cuts on and a seating orders by. A mean of logits is a different
    # column and agrees on every conclusion `stability_and_sheet_20260910` drew;
    # it is not what was approved, so it is not what ships.
    read = train.score_many(models, paths, transform, where, classes, config)
    probabilities = read.mean(axis=0)

    path = pool_scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    superseded = keep_superseded_pool_scores(log=log)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for key, probability in zip(keys, probabilities, strict=True):
            row = {
                "schema": SCHEMA,
                "head": HEAD,
                "run": column,
                "key": key,
            }
            for index in range(classes - 1):
                row[f"p_ge{index + 2}"] = float(probability[index])
            row["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(row) + "\n")

    record = {
        "run": column,
        "arm": arm,
        "seeds": chosen,
        "ships": RECIPES[check_recipe(recipe)]["ships"],
        "checkpoints": [tracked_name(one) for one in checkpoints],
        "averaged_on": "the probability scale",
        "candidates": len(keys),
        "below_the_bar_and_not_read": below,
        "below_the_bar_is": (
            "where this head's output is undefined. A score written there would exist only "
            "to be misread, so it is not written"
        ),
        "no_picture_on_disk": absent,
        "seconds": round(time.time() - began, 1),
        "wrote": str(path),
        "superseded": None if superseded is None else str(superseded),
        "superseded_is": (
            "the scores this write replaced, kept under the name of the run that made "
            "them. Every solve record taken before this one resolves its cascade order "
            "out of that file"
        ),
    }
    log(f"[{HEAD}] {len(keys):,} rows in {record['seconds']}s -> {path}")
    return record


def load_checkpoint(path: Path, device: str = "auto"):
    """Rebuild this head from a checkpoint. The config in the file decides how."""
    import torch

    from fractal_wallpapers.models import train

    where = train.device_of(device)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    model = head.build(
        num_classes=int(config["classes"]), backbone=config["backbone"], pretrained=False
    )
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


# --------------------------------------------------------------------------- #
# The bar, and the read of it.
# --------------------------------------------------------------------------- #
#: What the winning arm has to do, and the two incumbents it has to do it against.
#: Both are quantities a seating already has: `candidate_p_ge4` is the column the
#: gate emits, `rank_key` is what the seating currently ranks on. **Both, and not
#: the easier of the two** — [`curation.render_grade`] made exactly this
#: correction for the render judge, and it applies unchanged here: an arm that
#: beat the column and lost to the key would have improved nothing that ships.
GATED_INCUMBENTS = ("candidate_p_ge4", "rank_key")

#: The two statistics gated, at the boundary this head exists to order.
#: `auc_ge4` is 4-against-the-rest and `spearman` is the whole scale at once; a
#: head that moved one and not the other has not produced a fine order.
GATED_STATISTICS = ("auc_ge4", "spearman")


def write_bar(
    band_name: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
    force: bool = False,
    log=say,
) -> tuple[Path, dict]:
    """Register this band's bar, **before its runs exist**.

    The incumbent figures are copied in rather than referenced, so the bar stays
    readable a year from now without re-deriving anything, and so that a later
    re-fit of `rank_key` cannot quietly move the height a band was judged at.

    Refuses to overwrite. A bar rewritten after a band is a bar fitted to what
    happened, which is the whole thing pre-registration is for.
    """
    path = bar_path(band_name, corpus, recipe)
    if path.is_file() and not force:
        raise GradeTrainingError(
            f"{path} already exists, and a bar rewritten after its band is a bar fitted to "
            f"what happened. Pass force only to correct a bar no run has been read against."
        )
    read = baselines(corpus)
    incumbents = {}
    for name in GATED_INCUMBENTS:
        mine = read.get(name) or {}
        if any(mine.get(statistic) is None for statistic in GATED_STATISTICS):
            raise GradeTrainingError(
                f"the incumbent {name!r} cannot be read on the stopping slice, so a bar "
                f"stated against it would be a bar nothing could be judged by: {mine}"
            )
        incumbents[name] = {statistic: mine[statistic] for statistic in GATED_STATISTICS}
        incumbents[name]["rows"] = mine.get("rows_carrying_it")

    document = {
        "schema": SCHEMA,
        "head": HEAD,
        "band": str(band_name),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": check_recipe(recipe),
        "recipe_is": RECIPES[check_recipe(recipe)]["says"],
        "registered_at": _stamp(),
        "rule": (
            "the winning arm must beat BOTH incumbents on BOTH statistics at EVERY seed, "
            "strictly, on the held-out lineages. Any one of those failing is a FAIL for the "
            "band — there is no partial credit and no best-of"
        ),
        "gated": {"incumbents": list(GATED_INCUMBENTS), "statistics": list(GATED_STATISTICS)},
        "incumbents": incumbents,
        "population": {
            "rows": read.get("rows"),
            "base_rates": read.get("base_rates"),
            "slice": "gate_column" if read.get("gate_column_rows", 0) < read.get("rows") else "all",
            "gate_column_rows": read.get("gate_column_rows"),
            "gate_column_is": read.get("gate_column_is"),
            "is": (
                "the stopping slice — within-store held out, optimistic by one early stop, "
                "and drawn from a store that is not eval-eligible. This bar says which of "
                "three quantities orders these rows best and nothing about any other rows. "
                "Where `slice` is `gate_column` the heights and the arm are both read on "
                "the rows the incumbents exist for, and never on two different populations"
            ),
        },
        "does_not_gate": (
            "the arm ranking, the epoch, or anything about the pool. Adoption is a separate "
            "act and this bar does not authorize one"
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[{HEAD}] bar registered at {tracked_name(path)}")
    return path, document


def read_bar(band_name: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE) -> dict:
    path = bar_path(band_name, corpus, recipe)
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} does not exist. Register the bar before the band, so that what counts "
            f"as clearing it was decided without knowing what happened."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def acceptance(
    band_name: str = BAND, corpus: str = CORPUS, recipe: str = RECIPE, log=say
) -> tuple[Path, dict]:
    """Read the band against its registered bar, and write the verdict down.

    **Every seed of the winning arm, against every incumbent, on every gated
    statistic.** The record carries each of those cells whether it passed or not,
    because a verdict without its arithmetic is a verdict nobody can check.
    """
    bar = read_bar(band_name, corpus, recipe)
    read = band(seeds=SEEDS, band_name=band_name, corpus=corpus, recipe=recipe)
    winner = read["pick"]["arm"]
    mine = [row for row in read["runs"] if row["arm"] == winner]
    if not mine:
        raise GradeTrainingError(f"the winning arm {winner!r} has no fitted run")

    # Read on the slice the bar was stated over, and named on every cell: on the
    # corrected corpus the incumbents exist for four fifths of the stopping rows,
    # and an arm read over all of them would be a different population.
    stated = bar.get("population") or {}
    on = "held_out_on_the_gate_column" if stated.get("slice") == "gate_column" else ""
    cells, failures = [], []
    for row in mine:
        read_on = (row.get(on) if on else None) or row["held_out"]
        for incumbent, heights in bar["incumbents"].items():
            for statistic in bar["gated"]["statistics"]:
                ours = read_on.get(statistic)
                theirs = heights.get(statistic)
                passed = ours is not None and theirs is not None and float(ours) > float(theirs)
                cell = {
                    "seed": row["seed"],
                    "run": row["run"],
                    "read_on": on or "held_out",
                    "rows": read_on.get("rows"),
                    "incumbent": incumbent,
                    "statistic": statistic,
                    "arm": None if ours is None else round(float(ours), 4),
                    "incumbent_value": None if theirs is None else round(float(theirs), 4),
                    "margin": (
                        None
                        if ours is None or theirs is None
                        else round(float(ours) - float(theirs), 4)
                    ),
                    "verdict": "PASS" if passed else "FAIL",
                }
                cells.append(cell)
                if not passed:
                    failures.append(cell)

    verdict = "CLEARED" if not failures else "NOT CLEARED"
    margins = [cell["margin"] for cell in cells if cell["margin"] is not None]
    document = {
        "schema": SCHEMA,
        "head": HEAD,
        "band": str(band_name),
        "corpus": check_corpus(corpus),
        "recipe": check_recipe(recipe),
        "read_at": _stamp(),
        "bar": tracked_name(bar_path(band_name, corpus, recipe)),
        "registered_at": bar.get("registered_at"),
        "arm": winner,
        "seeds": [row["seed"] for row in mine],
        "verdict": verdict,
        "cells": cells,
        "failures": failures,
        "worst_margin": None if not margins else round(min(margins), 4),
        "says": (
            f"{verdict}: {len(cells) - len(failures)} of {len(cells)} gated cells pass. "
            f"The bar gates the arm and not the adoption — nothing here is wired in"
        ),
    }
    path = comparison_path(band_name, corpus, recipe)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[{HEAD}] {verdict}: worst margin {document['worst_margin']}")
    return path, document


def _stamp() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def selection_statistic(said: dict) -> float:
    """The number a run is ranked by inside its band: the rule's own, maximized.

    `best_selection_objective` is recorded negated because the loop minimizes, so
    this is the one place the sign is undone and every reader takes it from here.
    """
    return -float(said["best_selection_objective"])


def band(
    arms=None,
    seeds=SEEDS,
    band_name: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
) -> dict:
    """Every run of one band, the incumbents it is read beside, and the pick.

    **Arms are ranked by the MEAN of the band's own statistic over its seeds, and
    the winning arm ships its MEDIAN seed.** Both halves are deliberate. The mean
    is what says an arm is better rather than that one of its runs was; the median
    is what stops the band shipping a coin flip, because `more`'s surface across
    epochs is flat enough that cuDNN nondeterminism moves the argmax epoch by a
    dozen while the statistic barely moves. An argmax seed is the luckiest run of
    three and is not the run the band would give again.

    A median needs an odd count. With an even one this takes the **lower** of the
    two middle seeds and says so on the record — the conservative direction, and
    stated rather than silently rounded.
    """
    arms = tuple(arms if arms is not None else RECIPES[check_recipe(recipe)]["arms"])
    rows = []
    for arm in arms:
        for seed in seeds:
            try:
                said = read_run(arm, seed, band_name, corpus, recipe)
            except GradeTrainingError:
                continue
            rows.append(
                {
                    "arm": arm,
                    "seed": int(seed),
                    "run": said["run"],
                    "best_epoch": said["best_epoch"],
                    "selection": selection_statistic(said),
                    "rule": said.get("best_selection_rule"),
                    "trainable_share": said["freezing"]["trainable_share"],
                    "wall_seconds": said["wall_seconds"],
                    "held_out": said["held_out"],
                    # Absent on every run fitted before 2026-09-09, where the two
                    # were the same slice and the key was not written.
                    "held_out_on_the_gate_column": said.get("held_out_on_the_gate_column"),
                }
            )
    if not rows:
        raise GradeTrainingError(f"no run of band {band_name!r} has been fitted")

    per_arm: dict = {}
    for row in rows:
        per_arm.setdefault(row["arm"], []).append(row)
    summary = {}
    for arm, mine in sorted(per_arm.items()):
        values = [row["selection"] for row in mine]
        summary[arm] = {
            "seeds": len(values),
            "mean_selection": round(sum(values) / len(values), 4),
            "best_selection": round(max(values), 4),
            "worst_selection": round(min(values), 4),
            "spread": round(max(values) - min(values), 4),
        }
    winner = max(summary, key=lambda arm: summary[arm]["mean_selection"])
    ordered = sorted(per_arm[winner], key=lambda row: (row["selection"], row["seed"]))
    middle = (len(ordered) - 1) // 2
    picked = ordered[middle]

    return {
        "schema": SCHEMA,
        "head": HEAD,
        "band": str(band_name),
        "corpus": check_corpus(corpus),
        "corpus_is": CORPORA[check_corpus(corpus)]["says"],
        "recipe": check_recipe(recipe),
        "recipe_is": RECIPES[check_recipe(recipe)]["says"],
        "ships": RECIPES[check_recipe(recipe)]["ships"],
        "rule": RULES[str(band_name)]["says"],
        "statistic": f"{RULES[str(band_name)]['statistic']} at >={RULES[str(band_name)]['tier']}",
        "arms": summary,
        "pick": {
            "arm": winner,
            "seed": picked["seed"],
            "run": picked["run"],
            "of_seeds": [row["seed"] for row in ordered],
            "even_count_took_the_lower_middle": len(ordered) % 2 == 0,
        },
        "pick_rule": (
            "the arm with the highest MEAN of the band's own statistic over its seeds, at "
            "that arm's MEDIAN seed. Never the argmax: the epoch surface is flat enough "
            "that the best seed of three is a coin flip rather than a fact about the arm"
        ),
        "baseline": _baselines_or_reason(corpus),
        "baseline_is": (
            "the two incumbents over these same rows — the shipped judge's own "
            "`candidate_p_ge4`, which is the column, and `rank_key`, which is what a seating "
            "actually ranks on. An arm beating the column and losing to the key would have "
            "improved nothing anybody ships"
        ),
        "runs": sorted(rows, key=lambda row: (-row["selection"], row["run"])),
    }


def _baselines_or_reason(corpus: str = CORPUS) -> dict:
    """The baseline, or why it could not be read. A band is still worth writing
    without it, and a missing block that raised would take the table with it."""
    try:
        return baselines(corpus)
    except (GradeTrainingError, OSError) as unreadable:
        return {"unreadable": str(unreadable)}


def write_band(
    arms=None,
    seeds=SEEDS,
    band_name: str = BAND,
    corpus: str = CORPUS,
    recipe: str = RECIPE,
) -> tuple[Path, dict]:
    record = band(arms, seeds, band_name, corpus, recipe)
    path = band_path(band_name, corpus, recipe)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, record


__all__ = [
    "RULES",
    "CORPORA",
    "CORPUS",
    "BUILD_CORPUS",
    "PRE_EXISTING",
    "STRATA",
    "block_of",
    "check_corpus",
    "qualified",
    "sheet_of",
    "strata_of",
    "GATED_STATISTICS",
    "GATED_INCUMBENTS",
    "FIRST_BAND",
    "BAND_ARMS",
    "BAND",
    "write_bar",
    "selection_statistic",
    "readable_at",
    "read_bar",
    "comparison_path",
    "bar_path",
    "acceptance",
    "ARMS",
    "CARRIED",
    "EPOCHS",
    "HEAD",
    "HOLDOUT_SHARE",
    "INHERITANCE",
    "PATIENCE",
    "SCHEMA",
    "SEEDS",
    "SOURCE",
    "SPLIT_SEED",
    "GradeTrainingError",
    "Unit",
    "band",
    "baselines",
    "fit",
    "freeze",
    "head_dir",
    "initial_state",
    "objective",
    "population",
    "keep_superseded_pool_scores",
    "pool_scores_run",
    "read_population",
    "read_run",
    "superseded_pool_scores_path",
    "read_split",
    "recipe_from",
    "root",
    "run_dir",
    "run_name",
    "set_train_mode",
    "sides_for",
    "write_band",
    "write_population",
    "write_split",
]
