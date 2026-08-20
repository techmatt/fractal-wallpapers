"""The second bar: does one score decide the same thing at every regime, on stock?

The first cross-regime bar was read on the evaluation split and could not resolve
three of its four slices — 78% of that population reads below `P(≥3) = 0.05` at
every geometry, so it agrees with itself trivially and a rank correlation over it
starts at 0.99 with nowhere to go. See
[`fractal_wallpapers.models.regime_acceptance`]: a rho is a property of the
population as much as of the head, and a bar meant to resolve one has to be
written against rows where the score is contested.

This module writes that second bar. Three things change and nothing else does.

**The population is production stock**, the sidecar the intake ranks on — the
family the motivating numbers came from — stratified over partition × the
incumbent's own canonical score band so every band a decision could flip in is
represented rather than swamped by the mass below the junk floor. Every location
the label store holds is **excluded**: the candidate trained on those at all
three regimes and could have memorized their agreement.

**The statistic is a decision flip, not a rank.** A gate is a floor this project
already acts on, read on a probability the head already emits, and a flip is the
head's own cheap-regime read landing on the other side of that gate from its own
canonical read. Rank agreement was never the deliverable: the supply engine does
not rank across regimes, it *acts* at three thresholds, and the first read's own
report shows rank agreement surviving while decisions do not.

**The unit is the location.** The split's neighbourhood groups do not exist over
here — stock is drawn from walk ledgers, not from a labelled corpus — so the
paired bootstrap resamples locations and the record says so. Overlapping frames
from one walk are therefore counted as separate evidence, which is the honest
description of a draw over stock and is declared rather than discovered.

## No labels are made here, and the draw is model-score-conditioned

The strata are the incumbent's own scores, so this population is selected on a
model score. That disqualifies it as an instrument for anything about human
labels forever — and it is not one: nothing here reads a label. If a row drawn
here is ever labelled it is **train-side material** by the registry's own rule,
because a draw ordered by a head's score is exactly what
[`fractal_wallpapers.labeling.registry`] refuses eval-eligibility to.

## The candidate is the object under test, and it does not move

Nothing here trains. The band is the three seeds `regime_acceptance` already
selected, at the checkpoints it already chose, and the gated pick stays the seed
the frozen training-side selection rule named. A second read that re-picked a
seed would be choosing the winner on the arm that gates it.
"""

from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

from fractal_wallpapers.models import metrics, regime_acceptance, train
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record here carries.
SCHEMA = 1

#: The head this bar is about, and the runs on either side of it. The incumbent
#: is the shipped seed alone: the other two exist and the first bar reads them,
#: but a head that does not serve is not the thing being replaced.
HEAD = regime_acceptance.HEAD
INCUMBENT_RUN = regime_acceptance.SHIPPED_RUN
CANDIDATE_RUNS = regime_acceptance.CANDIDATE_RUNS

#: Which candidate seed the PRIMARY arm gates on. Not the median of the band and
#: not the best of it: the seed the training-side selection rule already froze,
#: so this read chooses nothing. The other two are read the same way and
#: reported, which is how a reader sees whether a difference is larger than the
#: band's own seed spread.
STAGED_RUN = "seed0_all_regimes"

#: How many locations the draw holds, and the seed it is drawn under. Declared in
#: the bar before anything is scored — see [`power`] for why this number.
DRAW_SIZE = 4000
DRAW_SEED = 0

#: Score bands the draw is stratified over, alongside partition. The edges are the
#: acting gates themselves plus a split of the two wide tails, so a decision that
#: could flip is not drowned by the mass that cannot.
BANDS = ((0.0, 0.05), (0.05, 0.20), (0.20, 0.50), (0.50, 0.80), (0.80, 1.01))

#: Draws and seed for every interval here. Fixed, and part of the bar.
DRAWS = 5000
BOOTSTRAP_SEED = 0

#: The partition the incumbent is worst on. Reported alone, never gated: the
#: first bar gated a slice of 71 rows in 24 clusters and learned nothing from it.
WORST_FAMILY = regime_acceptance.WORST_FAMILY

#: What a row of the draw carries out of the sidecar: everything a view is made
#: from, plus the picture the sidecar's own score was read off and the regime that
#: picture was drawn at — a sidecar holds rows read at two of them now.
DRAWN_FIELDS = ("key", "partition", "family", "viewport", "maxiter", "view", "regime")

#: The field on a stored score row the strata are cut on.
STOCK_FIELD = "p_ge3"


class FlipError(RuntimeError):
    """The draw, the render or the read cannot be done as written."""


def gates() -> tuple[dict, ...]:
    """The three decisions a location score makes, each read off its own owner.

    A gate is not restated here. `curation.floors` owns the junk floor and
    `supply.currency` owns the other two, and a bar that typed the numbers again
    would be a fourth opinion about where they are. Each row says which of them
    owns it, because a head flip has to restate all three and the restatement
    reads this list rather than assembling a fourth.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.supply import currency

    return (
        {
            "gate": "junk floor",
            "field": "p_ge3",
            "edge": floors.JUNK_FLOOR,
            "reads": f"P(>=3) >= {floors.JUNK_FLOOR}",
            "decides": "whether the intake spends colorize compute, and whether a walk stands here",
            "owner": "curation.floors.JUNK_FLOOR",
        },
        {
            "gate": "good floor",
            "field": "p_ge3",
            "edge": currency.GOOD_FLOOR,
            "reads": f"P(>=3) >= {currency.GOOD_FLOOR}",
            "decides": "whether a find is booked as a keeper",
            "owner": "supply.currency.GOOD_FLOOR",
        },
        {
            "gate": "great cut",
            "field": "p_ge4",
            "edge": currency.GREAT_CUT,
            "reads": f"P(>=4) >= {currency.GREAT_CUT}",
            "decides": "whether a keeper is a 4, which the currency weights ten to one",
            "owner": "supply.currency.GREAT_CUT",
        },
    )


def prereg_path(head: str = HEAD) -> Path:
    """The bar, written before a single row is scored."""
    return train.head_dir(head) / "flip_prereg.json"


def acceptance_path(head: str = HEAD) -> Path:
    """What the bar says about the band."""
    return train.head_dir(head) / "flip_acceptance.json"


def study_dir() -> Path:
    """Where the draw, its pictures and its reads live. Ignored, re-derivable."""
    return under("regime_flips")


def draw_path() -> Path:
    """The drawn population, written before it is rendered."""
    return study_dir() / "draw.jsonl"


def reads_path() -> Path:
    """Every run's probabilities at every regime, one line per location."""
    return study_dir() / "reads.jsonl"


def view_dir(regime: tile_module.Regime) -> Path:
    """Where one regime's pictures go.

    The canonical regime reads the shared deploy cache on purpose: the sidecar's
    own scores were read off those very files, so the arm that has to correspond
    to production is read off production's own pictures. The two cheaper regimes
    go under this study — they are addressed by their own digests and could share
    that cache safely, but the deploy cache is what a walk and an intake reach
    for and it should hold what they render.
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring

    if regime == tile_module.CANONICAL_REGIME:
        return discovery_scoring.view_dir()
    return study_dir() / regime.tag.lstrip("_")


def band_of(score: float) -> int:
    """Which stratum a score falls in."""
    for index, (low, high) in enumerate(BANDS):
        if low <= score < high:
            return index
    return len(BANDS) - 1


def eligible(head: str = HEAD) -> tuple[list[dict], dict]:
    """`(rows, census)` — sidecar stock with every labelled location removed.

    The exclusion is on the location identity the whole project keys on, not on a
    batch name: a location can reach the label store through any sheet, and the
    reason to drop it is that the candidate saw it at three regimes.
    """
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.labeling import store

    scores = intake.read_scores()
    labelled = {json.dumps(key, ensure_ascii=False) for key in store.resolved().current}
    kept, dropped, foreign = [], 0, 0
    for key, row in scores.items():
        if key in labelled:
            dropped += 1
            continue
        if row.get("head") != head:
            foreign += 1
            continue
        kept.append(row)
    kept.sort(key=lambda row: row["key"])
    census = {
        "sidecar_rows": len(scores),
        "labelled_and_excluded": dropped,
        "other_head_and_excluded": foreign,
        "eligible": len(kept),
        "by_partition": dict(sorted(Counter(row["partition"] for row in kept).items())),
        "by_band": {
            str(index): count
            for index, count in sorted(Counter(band_of(row[STOCK_FIELD]) for row in kept).items())
        },
    }
    return kept, census


def draw(rows: list[dict], want: int = DRAW_SIZE, seed: int = DRAW_SEED) -> list[dict]:
    """A sample spread over partition × score band, as evenly as the cells allow.

    Cells are filled round-robin from the smallest upward, so a thin partition
    contributes everything it has and the quota it cannot fill is spent on the
    partitions that can — rather than the draw silently becoming whichever
    partition the walks happened to find most of.
    """
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        cells[(row["partition"], band_of(row[STOCK_FIELD]))].append(row)
    # Shuffled in a deterministic cell order, from a deterministic starting order:
    # a draw that consumed the generator in the order the rows happened to arrive
    # would be a different sample every time the sidecar was written differently.
    generator = random.Random(seed)
    for key in sorted(cells):
        cells[key].sort(key=lambda row: row["key"])
        generator.shuffle(cells[key])

    order = sorted(cells, key=lambda key: (len(cells[key]), key))
    drawn: list[dict] = []
    taken: Counter = Counter()
    while len(drawn) < want:
        room = [key for key in order if taken[key] < len(cells[key])]
        if not room:
            break
        quota = max(1, (want - len(drawn)) // len(room))
        for key in room:
            if len(drawn) >= want:
                break
            take = min(quota, len(cells[key]) - taken[key], want - len(drawn))
            drawn.extend(cells[key][taken[key] : taken[key] + take])
            taken[key] += take
    return [
        {
            **{field: row[field] for field in DRAWN_FIELDS if field in row},
            "stock_p_ge3": row[STOCK_FIELD],
            "band": band_of(row[STOCK_FIELD]),
        }
        for row in drawn
    ]


def power(size: int = DRAW_SIZE) -> dict:
    """Why the draw is this big, in the numbers the bar is written against.

    A worst-case paired model: the pooled-over-gates flip rate is treated as one
    Bernoulli draw per location — every gate of a location flipping together,
    which is the correlation that costs the most — and the two heads' flips are
    treated as independent, so the discordant mass is the sum of the two rates
    rather than their difference. Both assumptions are pessimistic and stated;
    the realized numbers are read off the draw, never off this.
    """
    incumbent = 0.015
    reduction = 0.40
    difference = incumbent * reduction
    discordant = incumbent + incumbent * (1 - reduction)
    half_width = 1.96 * (discordant / size) ** 0.5
    return {
        "model": (
            "paired difference of two pooled flip rates, worst-case: every gate of a "
            "location flips together, and the two heads' flips are independent"
        ),
        "assumed_incumbent_pooled_flip_rate": incumbent,
        "assumed_reduction": reduction,
        "difference": difference,
        "half_width_at_this_size": half_width,
        "resolves": bool(half_width < difference),
        "size": size,
        "note": (
            "1-2% per gate is what the first bar measured on evaluation rows, and a 40% "
            "reduction is less than the halving it reported. The stratified production "
            "sample this draw follows measured 3-14% per gate, where the same test is far "
            "easier; the smaller assumption is the one the size is chosen against"
        ),
    }


def preregister(head: str = HEAD) -> dict:
    """The bar. Everything a verdict rests on, written before any number."""
    canonical = regime_acceptance.spelled(tile_module.CANONICAL_REGIME)
    cheaper = [regime_acceptance.spelled(regime) for regime in tile_module.BUILT_REGIMES[1:]]
    return {
        "schema": SCHEMA,
        "head": head,
        "study": "decision flips on production stock",
        "question": (
            "On the population the motivating numbers came from, does the regime-robust "
            "candidate cross the acting gates less often than the shipped head does when it "
            "reads the same location at a cheaper geometry?"
        ),
        "why_a_second_bar": (
            "the first one was read on the evaluation split, where 78% of rows sit below "
            "P(>=3)=0.05 at every geometry and agree trivially. Three of its four slices "
            "could not clear zero. This one is read where the score is contested"
        ),
        "population": {
            "rule": (
                "a fresh seeded draw over the curation sidecar, stratified over partition x "
                "the incumbent's own stored canonical score band"
            ),
            "source": "artifacts/curation/supply_scores.jsonl",
            "bands": [list(edges) for edges in BANDS],
            "size": DRAW_SIZE,
            "seed": DRAW_SEED,
            "excluded": (
                "every location the label store holds, on the project's own location "
                "identity. The candidate trained on those at all three regimes and could "
                "have memorized their cross-regime agreement"
            ),
            "score_conditioned": (
                "yes, and deliberately: the strata are a model's scores. No label is made "
                "here. If a row of this draw is ever labelled it is TRAIN-side material by "
                "the registry's own rule, because a draw ordered by a head's score is what "
                "eval-eligibility refuses"
            ),
            "power": power(),
        },
        "regimes": {
            "canonical": canonical,
            "cheaper": cheaper,
            "rendered": (
                "each drawn location at all three regimes, at the tile geometry the caches "
                "were built at, through the canonical view recipe. The canonical arm reads "
                "the shared deploy cache, which holds the very pictures the sidecar's own "
                "scores were read off"
            ),
        },
        "runs": {
            "incumbent": INCUMBENT_RUN,
            "candidate": list(CANDIDATE_RUNS),
            "gated_candidate": STAGED_RUN,
            "checkpoint": "best",
            "precision": "full precision on both sides, as the first bar declared",
            "why_this_seed": (
                "the staged pick by the frozen training-side selection rule. Not the median "
                "of the band and not its best: a second read that re-picked a seed would be "
                "choosing the winner on the arm that gates it"
            ),
        },
        "measure": {
            "unit": "one location, one head, one gate",
            "flip": (
                "the head's own read at a cheaper regime lands on the other side of a gate "
                "from its own read at the canonical regime. Both readings are the same head "
                "on the same location; nothing here compares a head to a label"
            ),
            "gates": [{key: gate[key] for key in ("gate", "reads", "decides")} for gate in gates()],
            "pooled": (
                "a head's pooled flip rate at a regime is its flipped decisions divided by "
                "three times the locations read"
            ),
        },
        "statistics": {
            "interval": (
                f"a 95 percent paired bootstrap, {DRAWS} draws at seed {BOOTSTRAP_SEED}, "
                "resampling LOCATIONS. Both heads are read on the same resampled rows"
            ),
            "why_locations": (
                "the split's neighbourhood groups do not exist over stock: these rows come "
                "from walk ledgers, not from a labelled corpus. Overlapping frames of one "
                "hot spot are therefore counted as separate evidence, which is declared "
                "rather than discovered"
            ),
            "direction": "LOWER IS BETTER, at every cell here",
        },
        "arms": {
            "primary": {
                "gated": True,
                "rule": (
                    "the pooled-over-gates flip rate of the gated candidate is significantly "
                    "LOWER than the incumbent's at EACH of the two cheaper regimes. A regime "
                    "passes when the upper bound of the paired interval on "
                    "(candidate - incumbent) is below zero. BOTH must pass"
                ),
                "regimes": cheaper,
            },
            "guard": {
                "gated": True,
                "rule": (
                    "none of the six regime x gate cells is significantly WORSE. A cell fails "
                    "when the lower bound of the paired interval on (candidate - incumbent) "
                    "is above zero"
                ),
                "cells": [f"{regime}|{gate['gate']}" for regime in cheaper for gate in gates()],
            },
        },
        "reported_not_gated": [
            f"the pooled flip rate of the {WORST_FAMILY} partition alone, per regime",
            "all three candidate seeds' numbers at every cell — the band",
            (
                "the raw Spearman rho of each head's own P(>=3) at a cheaper regime against "
                "its own at the canonical one, for continuity with the two earlier reads"
            ),
            "which direction the flips go, which the first read found nearly one-sided",
        ],
        "verdicts": {
            "PASS": "both cheaper regimes improve on the primary arm and no guard cell worsens",
            "FAIL": "anything else",
        },
        "outcome": {
            "PASS": (
                f"{STAGED_RUN} is staged as the candidate artifact beside the shipped head. "
                "The serving path is untouched: a location retrain moves the scale every "
                "floor is calibrated against, and restating those floors is a separate, "
                "priced decision"
            ),
            "FAIL": "nothing is staged, and the record says which cell",
        },
        "declared": [
            "This bar gates on a seed chosen elsewhere, unlike the first one, which read the "
            "median of the band. That is not a relaxation: the staged pick was frozen on the "
            "training side before this population existed, and reading the median here would "
            "let a second bar re-choose what the first one's selection rule already named.",
            "The population is model-score-conditioned by construction and can never measure "
            "anything about human labels. It measures a head against itself, which is the "
            "only claim made here.",
            "A flip is symmetric: a decision that turns on at the cheaper regime counts the "
            "same as one that turns off. The first read found the movement almost entirely "
            "one-directional, and the direction is reported rather than gated, because a "
            "gate that counted one direction only would reward a head that scores nothing.",
            "Locations, not groups, are the resampling unit — see statistics.why_locations.",
            "Nothing is trained, tuned or selected here. The band and its checkpoints are "
            "the ones the first bar already read.",
        ],
        "amendments": [],
    }


# --------------------------------------------------------------------------- #
# The render and the read.
# --------------------------------------------------------------------------- #
def _render(rows: list[dict], regime: tile_module.Regime, workers: int, log) -> tuple[list, dict]:
    """`(paths, tally)` — every drawn location's view at one regime.

    The regime is a parameter of the recipe, and the recipe is resolved **in the
    parent**: a render worker is handed a finished recipe and a finished output
    path, so it cannot decide what picture it is making. The digest that names a
    view already carries resolution and supersample, so two regimes cannot
    collide in one directory.
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring
    from fractal_wallpapers.models import location_view

    directory = view_dir(regime)
    directory.mkdir(parents=True, exist_ok=True)
    colormap = location_view.canonical_map()
    cyclic = location_view.cyclic_maps()
    paths = [location_view.view_path(row, colormap, cyclic, directory, regime) for row in rows]
    if regime == tile_module.CANONICAL_REGIME:
        _check_canonical_names(rows, paths)

    def task_for(index: int):
        return discovery_scoring.ViewTask(
            location_view.view_row(rows[index], colormap, cyclic, regime), str(paths[index])
        )

    wanted = [index for index, path in enumerate(paths) if not path.is_file()]
    started = time.monotonic()
    results = discovery_scoring.render_views([task_for(i) for i in wanted], workers, log)
    seconds = sum(result.seconds for result in results)
    failed = [index for index, result in zip(wanted, results, strict=True) if not result.ok]
    if failed:
        # Under a loaded machine the pooled engine occasionally dies with no
        # message, and a flip rate over whichever rows survived that is a
        # flip rate measured on a population the load chose.
        log(f"[flips] retrying {len(failed)} failed view(s) alone in the parent")
        retried = discovery_scoring.render_views([task_for(i) for i in failed], 1, log)
        seconds += sum(result.seconds for result in retried)
        failed = [index for index, result in zip(failed, retried, strict=True) if not result.ok]
    if failed:
        raise FlipError(
            f"{len(failed)} of {len(rows)} views would not render at "
            f"{regime_acceptance.spelled(regime)}. A population the engine chose is not "
            "the population the bar declared."
        )
    return paths, {
        "regime": regime_acceptance.spelled(regime),
        "directory": str(directory),
        "locations": len(rows),
        "rendered": len(wanted),
        "reused": len(rows) - len(wanted),
        "engine_seconds": round(seconds, 1),
        "wall_seconds": round(time.monotonic() - started, 1),
    }


def _check_canonical_names(rows: list[dict], paths: list[Path]) -> None:
    """The canonical view of a drawn row is the picture its sidecar score was read off.

    Recomputed rather than trusted: if the deploy recipe has moved since the
    sidecar was written, the canonical arm would be reading a different picture
    from the one the strata were cut on, and every flip rate here would be
    against a baseline that no longer exists.
    """
    canonical = tile_module.CANONICAL_REGIME.spelled
    odd = [
        row["key"]
        for row, path in zip(rows, paths, strict=True)
        # Only rows the sidecar scored at the deploy geometry name a picture this
        # arm would also make. A row scored at the node regime names the walk's
        # own gate render, which is a different regime's file and a different
        # name by construction — comparing the two would be reading the check
        # backwards.
        if row.get("view")
        and (row.get("regime") or canonical) == canonical
        and path.name != row["view"]
    ]
    if odd:
        raise FlipError(
            f"{len(odd)} drawn row(s) name a canonical view the deploy recipe no longer "
            f"makes (first: {odd[0]}). The sidecar's scores were read off those files, so "
            "the strata and the canonical arm would be two different pictures."
        )


def _read_through(run: str, paths_by_regime: dict, head: str, device: str, log) -> dict:
    """One checkpoint's probabilities over every regime's pictures.

    Loaded once and read three times: a run is a third of a gigabyte and the
    pictures are already on disk, so the alternative is four loads per regime for
    nothing.
    """
    from fractal_wallpapers.models import scoring as scoring_module

    checkpoint = train.checkpoint_path(head, "best", run)
    if not checkpoint.is_file():
        raise FlipError(f"{checkpoint} is missing: run {run!r} has no best checkpoint to read.")
    model, config, where = scoring_module.load(checkpoint, device)
    transform = scoring_module.transform_of(config)
    classes = int(config["classes"])
    out = {}
    for regime, paths in paths_by_regime.items():
        started = time.monotonic()
        out[regime] = train.score(model, paths, transform, where, classes, {"batch_size": 64})
        log(f"[flips] {run} at {regime}: {len(paths)} reads in {time.monotonic() - started:.0f}s")
    return {"probabilities": out, "classes": classes, "checkpoint": str(checkpoint)}


def score(
    head: str = HEAD,
    limit: int | None = None,
    workers: int | None = None,
    device: str = "auto",
    log=train.say,
) -> dict:
    """Draw, render at every regime, and read every run over every picture.

    `limit` renders and reads a prefix of the declared draw and writes nothing
    tracked — the rehearsal the render budget is estimated from. It is a
    measurement of the engine, not a smaller study: the bar's population is the
    whole draw and the verdict refuses anything else. Note that the draw is
    written cell by cell, so a *prefix* is one stratum and prices the engine on
    the cheapest material there is; a spread across the whole draw is what a
    budget should be taken on.

    `workers` defaults to the scorer's own, which is **one**. The fan-out loses
    at this regime the same way it loses at the canonical one — 60 uncached views
    at 640x360ss1 render at 2.45/s serially, 2.27/s at three workers and 2.14/s
    at six, and the engine-seconds inflate six-fold under contention while the
    wall clock gets worse. See [`fractal_wallpapers.discovery.scoring`].
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring
    from fractal_wallpapers.models import head as head_module

    workers = discovery_scoring.DEFAULT_WORKERS if workers is None else int(workers)
    bar = json.loads(prereg_path(head).read_text(encoding="utf-8"))
    stock, census = eligible(head)
    drawn = draw(stock, bar["population"]["size"], bar["population"]["seed"])
    if len(drawn) != bar["population"]["size"]:
        raise FlipError(
            f"the draw realized {len(drawn)} of the {bar['population']['size']} the bar "
            f"declares, over {census['eligible']} eligible rows. A bar's population is not "
            "whatever the cells could fill."
        )
    study_dir().mkdir(parents=True, exist_ok=True)
    draw_path().write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in drawn),
        encoding="utf-8",
        newline="\n",
    )
    rows = drawn if limit is None else drawn[: int(limit)]
    log(f"[flips] {census['eligible']} eligible, {len(drawn)} drawn, {len(rows)} being read")

    renders, paths_by_regime = {}, {}
    for regime in tile_module.BUILT_REGIMES:
        name = regime_acceptance.spelled(regime)
        log(f"[flips] rendering {len(rows)} view(s) at {name}")
        paths, tally = _render(rows, regime, workers, log)
        renders[name] = tally
        paths_by_regime[name] = [str(path) for path in paths]
        log(
            f"[flips] {name}: {tally['rendered']} rendered, {tally['reused']} reused, "
            f"{tally['engine_seconds']}s of engine in {tally['wall_seconds']}s"
        )

    read = {
        run: _read_through(run, paths_by_regime, head, device, log)
        for run in (INCUMBENT_RUN, *CANDIDATE_RUNS)
    }

    with reads_path().open("w", encoding="utf-8", newline="\n") as handle:
        for index, row in enumerate(rows):
            record = {
                "schema": SCHEMA,
                "head": head,
                "key": row["key"],
                "partition": row["partition"],
                "family": row["family"],
                "viewport": row["viewport"],
                "maxiter": row["maxiter"],
                "stock_p_ge3": row["stock_p_ge3"],
                "band": row["band"],
                "reads": {
                    run: {
                        regime: {
                            f"p_{head_module.cutpoint_label(cut)}": float(
                                read[run]["probabilities"][regime][index][cut]
                            )
                            for cut in range(read[run]["classes"] - 1)
                        }
                        for regime in paths_by_regime
                    }
                    for run in read
                },
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "schema": SCHEMA,
        "head": head,
        "census": census,
        "drawn": len(drawn),
        "read": len(rows),
        "rehearsal": limit is not None,
        "renders": renders,
        "checkpoints": {run: read[run]["checkpoint"] for run in read},
        "wrote": str(reads_path()),
    }


# --------------------------------------------------------------------------- #
# The judgement.
# --------------------------------------------------------------------------- #
def read_reads(path: Path | None = None) -> list[dict]:
    """The scored draw, schema-checked."""
    path = reads_path() if path is None else Path(path)
    if not path.is_file():
        raise FlipError(
            f"{path} is missing — nothing has read the draw yet. Run "
            f"`fractal-wallpapers regime flip-score` first."
        )
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise FlipError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


def _flips(rows: list[dict], run: str, regime: str, canonical: str, gate: dict):
    """A 0/1 column: did this head's decision at this gate move at this regime?"""
    import numpy

    field, edge = gate["field"], gate["edge"]
    here = numpy.array([row["reads"][run][regime][field] for row in rows], dtype=float)
    there = numpy.array([row["reads"][run][canonical][field] for row in rows], dtype=float)
    return ((here >= edge) != (there >= edge)).astype(float)


def _direction(rows: list[dict], run: str, regime: str, canonical: str, gate: dict) -> dict:
    """Which way the flips went: off at the cheaper regime, or on."""
    import numpy

    field, edge = gate["field"], gate["edge"]
    here = numpy.array([row["reads"][run][regime][field] for row in rows], dtype=float) >= edge
    there = numpy.array([row["reads"][run][canonical][field] for row in rows], dtype=float) >= edge
    return {"turned_off": int((there & ~here).sum()), "turned_on": int((~there & here).sum())}


def _interval(ours, theirs, unit) -> dict:
    """The paired interval on (candidate - incumbent), resampling locations."""
    import numpy

    ours = numpy.asarray(ours, dtype=float)
    theirs = numpy.asarray(theirs, dtype=float)

    def statistic(indices):
        return float(ours[indices].mean() - theirs[indices].mean())

    interval = metrics.bootstrap(statistic, unit, draws=DRAWS, seed=BOOTSTRAP_SEED)
    return {
        "candidate": float(ours.mean()),
        "incumbent": float(theirs.mean()),
        "delta": float(ours.mean() - theirs.mean()),
        "ci": [interval["lo"], interval["hi"]],
    }


def _verdict(interval: dict) -> str:
    """IMPROVED / WORSENED / NOT_RESOLVED, on a statistic where lower is better."""
    low, high = interval["ci"]
    if high is not None and high < 0:
        return "IMPROVED"
    if low is not None and low > 0:
        return "WORSENED"
    return "NOT_RESOLVED"


def read(head: str = HEAD, path: Path | None = None) -> dict:
    """The whole bar, read against the scored draw."""
    import numpy

    bar = json.loads(prereg_path(head).read_text(encoding="utf-8"))
    rows = read_reads(path)
    if len(rows) != bar["population"]["size"]:
        raise FlipError(
            f"{len(rows)} rows were read and the bar declares {bar['population']['size']}. A "
            "rehearsal is a measurement of the engine, not a smaller study."
        )
    canonical = regime_acceptance.spelled(tile_module.CANONICAL_REGIME)
    cheaper = [regime_acceptance.spelled(regime) for regime in tile_module.BUILT_REGIMES[1:]]
    runs = (INCUMBENT_RUN, *CANDIDATE_RUNS)
    unit = numpy.arange(len(rows))
    families = numpy.array([row["partition"] for row in rows])
    worst = numpy.where(families == WORST_FAMILY)[0]

    columns = {
        (run, regime, gate["gate"]): _flips(rows, run, regime, canonical, gate)
        for run in runs
        for regime in cheaper
        for gate in gates()
    }
    # A location's pooled value is the mean of its three gate flips, so the mean
    # over locations is exactly flipped decisions over three times the locations
    # — and the paired bootstrap has one number per location to resample.
    pooled = {
        (run, regime): numpy.mean(
            [columns[(run, regime, gate["gate"])] for gate in gates()], axis=0
        )
        for run in runs
        for regime in cheaper
    }

    primary = {}
    for regime in cheaper:
        entry = _interval(pooled[(STAGED_RUN, regime)], pooled[(INCUMBENT_RUN, regime)], unit)
        entry["verdict"] = _verdict(entry)
        entry["band"] = {run: float(pooled[(run, regime)].mean()) for run in CANDIDATE_RUNS}
        entry["gated_on"] = STAGED_RUN
        primary[regime] = entry

    guard = {}
    for regime in cheaper:
        for gate in gates():
            key = f"{regime}|{gate['gate']}"
            entry = _interval(
                columns[(STAGED_RUN, regime, gate["gate"])],
                columns[(INCUMBENT_RUN, regime, gate["gate"])],
                unit,
            )
            entry["verdict"] = _verdict(entry)
            entry["band"] = {
                run: float(columns[(run, regime, gate["gate"])].mean()) for run in CANDIDATE_RUNS
            }
            entry["direction"] = {
                run: _direction(rows, run, regime, canonical, gate)
                for run in (INCUMBENT_RUN, STAGED_RUN)
            }
            guard[key] = entry

    reported = {
        "worst_family": {
            "partition": WORST_FAMILY,
            "locations": int(len(worst)),
            "pooled": {
                regime: {run: float(pooled[(run, regime)][worst].mean()) for run in runs}
                for regime in cheaper
            }
            if len(worst)
            else {},
        },
        "spearman": {
            regime: {
                run: metrics.spearman(
                    numpy.array([row["reads"][run][regime]["p_ge3"] for row in rows]),
                    numpy.array([row["reads"][run][canonical]["p_ge3"] for row in rows]),
                )
                for run in runs
            }
            for regime in cheaper
        },
        "canonical_gate_pass_rates": {
            gate["gate"]: {
                run: float(
                    (
                        numpy.array(
                            [row["reads"][run][canonical][gate["field"]] for row in rows],
                            dtype=float,
                        )
                        >= gate["edge"]
                    ).mean()
                )
                for run in runs
            }
            for gate in gates()
        },
        "by_band": {
            str(index): int((numpy.array([row["band"] for row in rows]) == index).sum())
            for index in range(len(BANDS))
        },
        "by_partition": dict(sorted(Counter(row["partition"] for row in rows).items())),
    }

    failed = [regime for regime, entry in primary.items() if entry["verdict"] != "IMPROVED"]
    worsened = [key for key, entry in guard.items() if entry["verdict"] == "WORSENED"]
    verdict = "PASS" if not failed and not worsened else "FAIL"
    return {
        "schema": SCHEMA,
        "head": head,
        "prereg": tracked_name(prereg_path(head)),
        "prereg_question": bar["question"],
        "population": {
            "locations": len(rows),
            "side": "production stock, none of it in the label store",
            "seed": bar["population"]["seed"],
        },
        "runs": {"incumbent": INCUMBENT_RUN, "candidate": list(CANDIDATE_RUNS)},
        "gated_on": STAGED_RUN,
        "gates": [{key: gate[key] for key in ("gate", "reads")} for gate in gates()],
        "primary": primary,
        "guard": guard,
        "reported_not_gated": reported,
        "failed_cells": failed + worsened,
        "verdict": verdict,
    }


__all__ = [
    "BANDS",
    "BOOTSTRAP_SEED",
    "CANDIDATE_RUNS",
    "DRAWS",
    "DRAW_SEED",
    "DRAW_SIZE",
    "HEAD",
    "INCUMBENT_RUN",
    "SCHEMA",
    "STAGED_RUN",
    "WORST_FAMILY",
    "FlipError",
    "acceptance_path",
    "band_of",
    "draw",
    "draw_path",
    "eligible",
    "gates",
    "power",
    "preregister",
    "prereg_path",
    "read",
    "read_reads",
    "reads_path",
    "score",
    "study_dir",
    "view_dir",
]
