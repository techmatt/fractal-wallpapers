"""The bar the palette head is read against, written before it exists.

## The question is equivalence, not quality

The other three heads are asked *are you as good as the head you replace*, and
they are read against a human-labeled sheet that says what good is. This one
cannot be: there is no human palette-preference corpus in this repository, which
is the whole reason it is distilled rather than trained. So the question here is
narrower and more answerable — **does the student choose what the teacher would
choose** — and the honest way to write that down is to say plainly what it does
not establish. It does not establish that either of them is right. If the teacher
has a taste nobody shares, this head inherits it exactly, and the acceptance read
will say PASS.

## The population is what a production run really asked

180 candidate sets, vendored from the source project's last colorize-path batch:
each one a real location, the palette flavour a real deficit model assigned it,
and the maps its head really chose between. Nothing about them was generated for
this exercise, none of their locations is in the distillation corpus, and the
sets are up to thirty-two flavour-tight maps where the corpus's are eight drawn
uniformly — so the head is judged on a **harder** population than it trained on,
which is the direction an unmatched difference should point.

Both readings are taken on this repository's own renders of those candidates,
through the same transform, so what is compared is two functions rather than two
rendering pipelines.

## Where the bar comes from

An equivalence bar needs a number for *how much disagreement is already normal*,
and inventing one would make the verdict a matter of taste. There is a real one
available and it is measured on this very population: the **renderer control** —
how often the teacher, re-read here on this repository's pictures, picks the map
the production run recorded on the source project's pictures. That is the same
head, the same weights and the same candidate set, disagreeing with itself
because the picture changed. A student cannot sensibly be asked to track the
teacher more closely than a change of renderer already fails to.

The rule is declared here; the number is measured afterwards, exactly as the
finished-render bars declare a margin rule and read the source's own control to
fill it in.

That control is a ceiling, not a floor, so a second bar is stated in absolute
terms: on more than half of real sets the student must colour the picture with
the map the teacher would have chosen. Both have to hold. A control that came
back very low would otherwise let a poor student through on a technicality.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.models import metrics, palette_head, palette_scoring, palette_sets

#: The schema the pre-registration and the read both carry.
SCHEMA = 1

#: Draws in the bootstrap, and its seed. The cluster is the SET: a set's
#: candidates are the same location in different colours and are anything but
#: independent, so the unit that is resampled is the whole set.
DRAWS = 5000
BOOTSTRAP_SEED = 0

#: The absolute floor on top-pick agreement. More than half of real sets coloured
#: exactly as the teacher would colour them. Below that, "approximately
#: equivalent" is not a description of anything.
AGREEMENT_FLOOR = 0.50

#: The floor on the median per-set rank correlation. The student may disagree
#: about which of two near-equal maps wins; it may not disagree about the shape
#: of the preference.
ORDERING_FLOOR = 0.70

#: The ceiling on mean normalized regret: the share of a set's own teacher-score
#: spread that is given up, on average, by taking the student's pick instead of
#: the teacher's. A tenth. Stated normalized because the teacher's units mean
#: nothing on their own and a set whose candidates it rated within a hair of each
#: other cannot lose much by picking the wrong one.
REGRET_CEILING = 0.10


class AcceptanceError(RuntimeError):
    """The head cannot be read against its bar."""


def head_dir(run: str | None = None) -> Path:
    from fractal_wallpapers.models import palette_train

    return palette_train.head_dir(run)


def prereg_path() -> Path:
    return head_dir() / "prereg.json"


def acceptance_path() -> Path:
    return head_dir() / "acceptance.json"


def population() -> dict:
    """What the vendored sets hold, counted rather than claimed."""
    from collections import Counter

    sets = palette_sets.read()
    sizes = [len(row["candidates"]) for row in sets]
    return {
        "record": str(palette_sets.sets_path().relative_to(head_dir().parents[1])).replace(
            "\\", "/"
        ),
        "source_batch": palette_sets.SOURCE_BATCH,
        "sets": len(sets),
        "locations": len({(repr(row["family"]), repr(row["viewport"])) for row in sets}),
        "candidates": sum(sizes),
        "set_sizes": dict(sorted(Counter(sizes).items())),
        "flavours": len({row["flavour"] for row in sets}),
        "partitions": dict(sorted(Counter(row["partition"] for row in sets).items())),
        "blind": (
            "no location here is in the distillation corpus, and none of these sets was "
            "generated for this exercise: each is a real colorize decision the source "
            "project recorded"
        ),
    }


def preregister() -> dict:
    """Write the bar. Everything here is decided before a head exists."""
    document = {
        "schema": SCHEMA,
        "head": "palette",
        "question": (
            "Is a palette head distilled inside this repository approximately equivalent to "
            "the teacher it was distilled from — does it choose the same map — on the real "
            "candidate sets a production colorize run put in front of that teacher, both read "
            "on this repository's own pictures?"
        ),
        "population": population(),
        "declared": [
            "THE TEACHER IS THE GROUND TRUTH, NOT A HUMAN. Every arm here measures agreement "
            "with a pretrained head. A PASS says the student reproduces it; it says nothing "
            "at all about whether either of them picks the palette a person would.",
            "NOT A SAME-INPUT COMPARISON WITH THE PRODUCTION RUN. The recorded winners were "
            "chosen on the source project's own coarse recolors; every score read here is "
            "taken on a 640x360 render made by this engine through this colormap library. "
            "That gap is not assumed away — it is the renderer control, and it is measured "
            "on this same population and used to calibrate the bar.",
            "THE JUDGED SETS ARE HARDER THAN THE TRAINED ONES. A set here is one palette "
            "flavour's members, up to 32 maps that already resemble each other; a training "
            "set is 8 maps drawn uniformly from the whole pool. The flavour taxonomy is an "
            "artifact of the source project's clustering and does not exist in this "
            "repository, so it could not be reproduced in the draw.",
            "180 SETS RESOLVE A SHARE TO ABOUT PLUS OR MINUS 0.07. A difference smaller than "
            "the interval is reported as a band and is not called in either direction.",
            "THE POOL IS A SUBSET. 700 of the source pool's 987 maps are held here — every "
            "map a tracked corpus row or a vendored set names. A candidate set is complete; "
            "the pool the corpus draws from is not the whole production pool.",
        ],
        "rules": {
            "cluster": "the SET — its candidates are one location in different colours",
            "draws": DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "seeds": (
                "three, and the band is the answer. What ships is the MEDIAN seed by the "
                "top_pick arm, never the best of three."
            ),
        },
        "arms": {
            "top_pick": {
                "gated": True,
                "statistic": (
                    "the share of sets where the student's highest-scoring candidate is the "
                    "teacher's highest-scoring candidate, both read on the same pictures"
                ),
                "bars": [
                    {
                        "name": "renderer control",
                        "rule": (
                            "at least the share of sets on which the TEACHER, re-read here on "
                            "this repository's pictures, picks the map the production run "
                            "recorded. Same weights, same candidate set, disagreeing with "
                            "itself because the picture changed — a student cannot be asked "
                            "to track the teacher more closely than a change of renderer "
                            "already fails to."
                        ),
                        "value": "MEASURED AFTER THIS FILE IS WRITTEN, on this population",
                    },
                    {
                        "name": "floor",
                        "rule": "at least half of real sets coloured as the teacher would",
                        "value": AGREEMENT_FLOOR,
                    },
                ],
                "verdict": "PASS only if both bars hold on the point estimate",
            },
            "ordering": {
                "gated": True,
                "statistic": "the median per-set Spearman correlation, student against teacher",
                "bar": ORDERING_FLOOR,
                "why": (
                    "the top pick is one number out of a set of thirty-two, and a head that "
                    "agreed about the winner while shuffling the rest would be agreeing by "
                    "luck. This arm reads the whole vector's order."
                ),
            },
            "regret": {
                "gated": True,
                "statistic": (
                    "the mean, over sets, of (the teacher's score for its own pick minus its "
                    "score for the student's pick) divided by that set's teacher-score spread"
                ),
                "bar": REGRET_CEILING,
                "why": (
                    "a disagreement over two candidates the teacher rated within a hair of "
                    "each other costs nothing, and a bare agreement rate cannot tell that "
                    "from picking something the teacher put near the bottom. This arm is what "
                    "the choice actually costs, in the teacher's own units, normalized by how "
                    "much was at stake."
                ),
            },
            "interface": {
                "gated": True,
                "rule": (
                    "the checkpoint emits one finite score per picture and the score file "
                    "carries, for every set, a score for every candidate in the order the "
                    "set lists them"
                ),
            },
            "production_argmax": {
                "gated": False,
                "rule": (
                    "how often the student picks the map the production run recorded. "
                    "Reported beside the renderer control because both are cross-renderer "
                    "readings and neither is the thing the student is scored against."
                ),
            },
        },
        "fp16": {
            "gated_at": "ship, not here",
            "rules": [
                "every floating tensor cast to half precision and the artifact bit-identical "
                "on re-read",
                "at most 1% of sets change their top pick",
                "at most 8 discordant candidate pairs in any one set",
            ],
        },
    }
    head_dir().mkdir(parents=True, exist_ok=True)
    prereg_path().write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return document


def prereg() -> dict:
    path = prereg_path()
    if not path.is_file():
        raise AcceptanceError(
            f"{path} is missing. The bar is written before the head is read, never after: "
            f"pre-register first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _share(flags) -> float:
    return sum(1 for flag in flags if flag) / max(len(flags), 1)


def _interval(values, statistic) -> dict:
    import numpy

    array = numpy.asarray(values, dtype=numpy.float64)
    return metrics.bootstrap(
        lambda indices: statistic(array[indices]),
        list(range(len(array))),
        draws=DRAWS,
        seed=BOOTSTRAP_SEED,
    )


def measure(rows: list[dict]) -> dict:
    """One run's numbers on the vendored sets. No verdicts here — see [`read`]."""
    import numpy

    agreed = [1.0 if row["agreed"] else 0.0 for row in rows]
    correlations = [row["spearman"] for row in rows if row["spearman"] is not None]
    normalized = [
        row["regret"] / row["teacher_spread"] if row["teacher_spread"] > 0 else 0.0 for row in rows
    ]
    matched_production = [1.0 if row["pick"] == row["recorded_pick"] else 0.0 for row in rows]
    control = [1.0 if row["teacher_pick"] == row["recorded_pick"] else 0.0 for row in rows]
    swaps = [row["discordant_pairs"] for row in rows]
    return {
        "sets": len(rows),
        "top_pick_agreement": float(numpy.mean(agreed)),
        "top_pick_interval": _interval(agreed, numpy.mean),
        "median_spearman": float(numpy.median(correlations)) if correlations else None,
        "spearman_interval": _interval(correlations, numpy.median) if correlations else None,
        "spearman_below_half": int(sum(1 for value in correlations if value < 0.5)),
        "mean_normalized_regret": float(numpy.mean(normalized)),
        "median_normalized_regret": float(numpy.median(normalized)),
        "p90_normalized_regret": float(numpy.percentile(normalized, 90)),
        "regret_interval": _interval(normalized, numpy.mean),
        "renderer_control": float(numpy.mean(control)),
        "production_argmax": float(numpy.mean(matched_production)),
        "discordant_pairs": {
            "median": float(numpy.median(swaps)),
            "max": int(max(swaps)) if swaps else 0,
        },
        "teacher_spread": {
            "median": float(numpy.median([row["teacher_spread"] for row in rows])),
            "min": float(min(row["teacher_spread"] for row in rows)),
        },
    }


def _interface_arm(rows: list[dict]) -> dict:
    import math

    sets = {row["set"]: row for row in palette_sets.read()}
    complaints = []
    for row in rows:
        expected = sets.get(row["set"])
        if expected is None:
            complaints.append(f"set {row['set']} is not in the vendored record")
            continue
        if row["candidates"] != expected["candidates"]:
            complaints.append(f"set {row['set']} lists different candidates from the record")
        if len(row["score"]) != len(row["candidates"]):
            complaints.append(f"set {row['set']} carries {len(row['score'])} scores")
        if any(not math.isfinite(value) for value in row["score"]):
            complaints.append(f"set {row['set']} carries a non-finite score")
    return {
        "gated": True,
        "sets": len(rows),
        "complaints": complaints[:5],
        "held": not complaints,
    }


def read(runs: list[str | None] | None = None) -> dict:
    """Read every seed against the bar and write the verdict."""
    import numpy

    bar = prereg()
    runs = list(runs) if runs else [None]
    by_run, measured = {}, {}
    for name in runs:
        rows = palette_scoring.read(name)
        by_run[name or "root"] = rows
        measured[name or "root"] = measure(rows)

    controls = {value["renderer_control"] for value in measured.values()}
    if len(controls) != 1:
        raise AcceptanceError(
            f"the renderer control differs across runs ({sorted(controls)}). It is a fact "
            f"about the teacher and the population and cannot depend on which student was "
            f"scored beside it — one of these score files was written against a different "
            f"set of pictures."
        )
    control = controls.pop()

    ordered = sorted(measured, key=lambda name: measured[name]["top_pick_agreement"])
    median_run = ordered[len(ordered) // 2]
    reading = measured[median_run]

    arms = {
        "top_pick": {
            "gated": True,
            "ours": reading["top_pick_agreement"],
            "interval": reading["top_pick_interval"],
            "bars": {"renderer_control": control, "floor": AGREEMENT_FLOOR},
            "held": reading["top_pick_agreement"] >= control
            and reading["top_pick_agreement"] >= AGREEMENT_FLOOR,
            "band": sorted(value["top_pick_agreement"] for value in measured.values()),
        },
        "ordering": {
            "gated": True,
            "ours": reading["median_spearman"],
            "interval": reading["spearman_interval"],
            "bar": ORDERING_FLOOR,
            "sets_below_half": reading["spearman_below_half"],
            "held": reading["median_spearman"] is not None
            and reading["median_spearman"] >= ORDERING_FLOOR,
            "band": sorted(
                value["median_spearman"]
                for value in measured.values()
                if value["median_spearman"] is not None
            ),
        },
        "regret": {
            "gated": True,
            "ours": reading["mean_normalized_regret"],
            "median": reading["median_normalized_regret"],
            "p90": reading["p90_normalized_regret"],
            "interval": reading["regret_interval"],
            "bar": REGRET_CEILING,
            "held": reading["mean_normalized_regret"] <= REGRET_CEILING,
            "band": sorted(value["mean_normalized_regret"] for value in measured.values()),
        },
        "interface": _interface_arm(by_run[median_run]),
        "production_argmax": {
            "gated": False,
            "ours": reading["production_argmax"],
            "renderer_control": control,
            "note": (
                "both are cross-renderer readings: the control is the teacher disagreeing "
                "with its own recorded choice because the picture changed, and ours is the "
                "student's distance from that same recorded choice"
            ),
        },
    }
    gated = [arm for arm in arms.values() if arm.get("gated")]
    verdict = "PASS" if all(arm["held"] for arm in gated) else "FAIL"

    document = {
        "schema": SCHEMA,
        "head": "palette",
        "verdict": verdict,
        "shipped_run": median_run,
        "shipped_rule": "the median seed by the top_pick arm, never the best of three",
        "runs": {name: measured[name] for name in sorted(measured)},
        "arms": arms,
        "population": bar["population"],
        "declared": bar["declared"],
        "band_width": float(numpy.ptp([value["top_pick_agreement"] for value in measured.values()]))
        if len(measured) > 1
        else 0.0,
    }
    acceptance_path().write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return document


def fp16_agreement(before: list[dict], after) -> dict:
    """How much the half-precision head moved, in the units this head is read in.

    The two things the ratified shipping recipe protects, spelled for a head
    whose answer is a choice inside a set rather than a tier: **decisions** are
    the top picks, and **ordering** is counted in discordant candidate pairs
    inside a set — the same quantum a rank swap is, on a population of eight to
    thirty-two rather than of a hundred and fifty.
    """
    import numpy

    changed, swaps = 0, []
    for row, scores in zip(before, after, strict=True):
        swaps.append(metrics.discordant_pairs(row["score"], scores))
        changed += int(palette_head.top_pick(row["score"]) != palette_head.top_pick(scores))
    moves = numpy.abs(
        numpy.concatenate([numpy.asarray(row["score"]) for row in before])
        - numpy.concatenate([numpy.asarray(scores) for scores in after])
    )
    return {
        "sets": len(before),
        "decisions": {"changed": changed, "share": changed / max(len(before), 1)},
        "ordering": {"worst_discordant_pairs": int(max(swaps)) if swaps else 0, "swaps": swaps},
        "row_moves": {
            "median": float(numpy.median(moves)),
            "p99": float(numpy.percentile(moves, 99)),
            "worst": float(moves.max()),
        },
    }


__all__ = [
    "AGREEMENT_FLOOR",
    "BOOTSTRAP_SEED",
    "DRAWS",
    "ORDERING_FLOOR",
    "REGRET_CEILING",
    "SCHEMA",
    "AcceptanceError",
    "acceptance_path",
    "fp16_agreement",
    "head_dir",
    "measure",
    "population",
    "prereg",
    "prereg_path",
    "preregister",
    "read",
]
