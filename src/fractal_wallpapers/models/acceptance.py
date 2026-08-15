"""The bar a head has to clear, written down before the head exists.

## Why the file comes first

A bar chosen after the numbers are in is not a bar. So the pre-registration is
its own record, written and committed before the trainer runs, and this module
does two separate things that are never allowed to happen in one step:
[`preregister`] builds the bar out of the incumbent's committed scores and the
population's own shape, and [`read`] takes a trained head's scores and reports
what the bar says about them. The bar is loaded from the file; nothing in the
read may invent one.

## The population, and the one thing to know about it

The comparison runs over the locations that are on the **evaluation side of both
projects**. Here that is all 1,002 of this repository's evaluation side, because
every one of them came across as a score-unconditioned instrument the source
project also held out. The two corpora map location for location — 11,303 of
11,303, on the `c`-inclusive coordinate, with zero label disagreements — so the
join is exact rather than approximate.

**It is not a same-input comparison.** Each head is scored through *its own*
deploy view of the same location: the incumbent through its renderer's tile, this
one through this engine's. What is being compared is two whole pipelines against
one set of human verdicts, which is the comparison that means something and is
also the only one available.

**624 of the 1,002 were the incumbent's own checkpoint-selection population.** It
picked its epoch by maximizing average precision at the first cutpoint over them.
That makes the yardstick *generous to the incumbent* — most at the first
cutpoint, second-order at the two above it — and it is declared rather than
corrected, because the alternative is a 378-row subset with fourteen positives at
the wallpaper cutpoint and none at all at the release cutpoint. That subset is
reported and is explicitly not a decision surface.

## Both sides are read the same way

The incumbent's committed columns are per-cutpoint conditional probabilities. So
are this head's. Both are turned into unconditional probabilities by the same
running product before anything is measured — see
[`fractal_wallpapers.models.head.probabilities`]. Reading one side one way and
the other side the other way would be worth seven points of AUC at the release
cutpoint, which is larger than anything this comparison is trying to detect.

## The thin partitions, and the rule that stops them being quoted

Four of this repository's ten partitions have **no** location above the wallpaper
cutpoint on the evaluation side, and one has no evaluation rows at all. A
per-partition AUC computed there is not a weak measurement, it is not a
measurement: so a partition is reported only when it holds at least
[`MIN_POSITIVES`] positives at that cutpoint, and otherwise says
`NOT_MEASURABLE` with the count that made it so. No per-partition number gates
anything.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.models import head, metrics, train
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.supply.location import location_key

#: The schema the pre-registration and the read both carry.
SCHEMA = 1

#: How many positives a slice needs before an AUC over it is quoted at all.
#: Below it the number is dominated by which handful of locations landed there.
MIN_POSITIVES = 10

#: The floor on "materially worse", in AUC. Below this, a difference is inside
#: what a fresh seed and a fresh rendering pipeline move on their own.
MATERIAL_FLOOR = 0.02

#: Differences smaller than this are not called in prose, at any cutpoint: label
#: noise at the wallpaper boundary is larger than they are.
NOT_CALLED = 0.01

#: Draws in the cluster bootstrap, and its seed.
DRAWS, BOOTSTRAP_SEED = 5000, 0

#: The three seeds of the incumbent's control arm.
INCUMBENT_ARMS = ("mnv4_conv_medium_s0", "mnv4_conv_medium_s1", "mnv4_conv_medium_s2")

#: Where the incumbent's committed scores are extracted from, when the bar is
#: first written. Both files are read-only, both live outside this repository,
#: and neither is ever written to. Resolved beside this checkout rather than
#: from an absolute path — the source project is a sibling during the build era
#: and absent afterwards, which is exactly why the yardstick is vendored.
INCUMBENT_SCORES = Path("fractal-maker/data/backbone_search/eval_scores_backbone_v1.jsonl")
INCUMBENT_MANIFEST = Path("fractal-maker-artifacts/data/v11/manifest.jsonl")


def beside(relative: Path) -> Path:
    """A sibling checkout's file, from this one's location."""
    from fractal_wallpapers.paths import repo_root

    return repo_root().parent / relative


#: How the incumbent's family vocabulary maps onto this project's. Its names
#: fold the degree into the family word; here the degree is its own field, and
#: the partition is derived from the pair.
INCUMBENT_FAMILIES = {
    "mandelbrot": ("mandelbrot", 2),
    "multibrot3": ("multibrot", 3),
    "multibrot4": ("multibrot", 4),
    "multibrot5": ("multibrot", 5),
    "julia": ("julia", 2),
    "julia_multibrot3": ("julia", 3),
    "julia_multibrot4": ("julia", 4),
    "julia_multibrot5": ("julia", 5),
    "phoenix": ("phoenix", 2),
}


def prereg_path(name: str = "location") -> Path:
    """The bar, as it was written before the head existed."""
    return train.head_dir(name) / "prereg.json"


def yardstick_path(name: str = "location") -> Path:
    """The incumbent's scores on this population, vendored.

    Tracked, and that is the point: the source project is a sibling checkout
    during the build era and gone afterwards. A bar whose yardstick lives in
    another repository is a bar nobody can re-read, so the numbers the comparison
    runs against are copied in once, when the bar is written, and never again.
    """
    return train.head_dir(name) / "yardstick.jsonl"


def acceptance_path(name: str = "location") -> Path:
    """The read against it."""
    return train.head_dir(name) / "acceptance.json"


def _incumbent_family(row: dict) -> dict:
    kind, degree = INCUMBENT_FAMILIES[row["fractal_type"]]
    family = {"kind": kind, "degree": degree}
    for constant, (real, imaginary) in (
        ("c", ("c_re", "c_im")),
        ("p", ("p_re", "p_im")),
        ("z_prev", ("zm1_re", "zm1_im")),
    ):
        if row.get(real) is not None:
            family[constant] = [row[real], row[imaginary]]
    return family


def extract(scores: Path | None = None, manifest: Path | None = None) -> dict[int, dict]:
    """The incumbent's committed scores, keyed on **this** project's location id.

    Its own row ids mean nothing here, so the join goes through the location
    coordinate — the same `c`-inclusive key the evaluation pin is asserted at —
    and lands on the id this repository's tile build uses. That is the whole
    trick, and it is why neither project had to be told about the other.
    """
    scores = beside(INCUMBENT_SCORES) if scores is None else Path(scores)
    manifest = beside(INCUMBENT_MANIFEST) if manifest is None else Path(manifest)
    by_location = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = location_key(
            _incumbent_family(row),
            {"center_re": row["cx"], "center_im": row["cy"], "width": row["fw"]},
        )
        by_location[int(row["loc_id"])] = (tile_module.location_id(key), int(row["label"]))

    out = {}
    for line in scores.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        found = by_location.get(int(row["loc_id"]))
        if found is None:
            continue
        identifier, label = found
        entry = {
            "label": label,
            "population": row.get("population"),
            "role": row.get("eval_role"),
        }
        for arm in INCUMBENT_ARMS:
            conditional = [row[f"{arm}_p{tier}"] for tier in (2, 3, 4)]
            entry[arm] = _running_product(conditional)
        out[identifier] = entry
    return out


def vendor(control: dict[int, dict], name: str = "location") -> Path:
    """Write the yardstick down, one row per location. Returns the path."""
    path = yardstick_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for identifier, entry in sorted(control.items()):
            row = {"schema": SCHEMA, "location_id": identifier, **entry}
            handle.write(json.dumps(row) + "\n")
    return path


def incumbent(name: str = "location") -> dict[int, dict]:
    """The vendored yardstick — what every read of the bar is measured against."""
    path = yardstick_path(name)
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing. It is written when the bar is, from the source project's "
            "committed scores; without it there is nothing to compare a head to."
        )
    out = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        out[int(row["location_id"])] = {
            key: value for key, value in row.items() if key not in ("schema", "location_id")
        }
    return out


def _running_product(conditional: list[float]) -> list[float]:
    """The same reading this head's own probabilities get. See the module docs."""
    out, carried = [], 1.0
    for value in conditional:
        carried *= float(value)
        out.append(carried)
    return out


def yardstick(rows: list[dict], control: dict[int, dict], classes: int = head.CLASSES) -> dict:
    """What the incumbent measures on this population, per seed and as a band."""
    import numpy

    labels = numpy.array([row["score"] for row in rows])
    out: dict = {"locations": len(rows), "arms": list(INCUMBENT_ARMS), "cutpoints": {}}
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        truth = (labels >= index + 2).astype(int)
        seeds = {}
        for arm in INCUMBENT_ARMS:
            column = numpy.array([control[row["location_id"]][arm][index] for row in rows])
            seeds[arm] = metrics.auc(truth, column)
        values = [value for value in seeds.values() if value is not None]
        out["cutpoints"][label] = {
            "positives": int(truth.sum()),
            "per_seed": {arm: seeds[arm] for arm in INCUMBENT_ARMS},
            "band": [min(values), max(values)] if values else None,
            "spread": (max(values) - min(values)) if values else None,
            "mean": (sum(values) / len(values)) if values else None,
        }
    return out


def seed_precision(rows: list[dict], control: dict[int, dict], classes: int = head.CLASSES) -> dict:
    """How precisely this population can tell two heads apart at all.

    Measured on the incumbent's own three seeds: the widest paired interval
    between any two of them is the resolution the population offers, and a margin
    below it would be a bar the instrument cannot read.
    """
    import numpy

    labels = numpy.array([row["score"] for row in rows])
    groups = numpy.array([row["group"] for row in rows])
    out = {}
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        truth = (labels >= index + 2).astype(int)
        widest = 0.0
        pairs = {}
        for first in range(len(INCUMBENT_ARMS)):
            for second in range(first + 1, len(INCUMBENT_ARMS)):
                a, b = INCUMBENT_ARMS[first], INCUMBENT_ARMS[second]
                delta = metrics.paired_delta(
                    truth,
                    numpy.array([control[row["location_id"]][a][index] for row in rows]),
                    numpy.array([control[row["location_id"]][b][index] for row in rows]),
                    groups,
                    draws=DRAWS,
                    seed=BOOTSTRAP_SEED,
                )
                if delta["lo"] is not None:
                    widest = max(widest, -delta["lo"], -delta["hi"])
                    pairs[f"{a} vs {b}"] = {
                        "delta": delta["delta"],
                        "ci": [delta["lo"], delta["hi"]],
                    }
        out[label] = {"widest_lower_bound": widest, "pairs": pairs}
    return out


def margin_of(lower_bound: float) -> float:
    """The margin at one cutpoint: the floor, or what the control seeds need.

    Rounded up to the nearest half point of AUC so the number in the record is a
    decision rather than the tail of a bootstrap.
    """
    import math

    calibrated = math.ceil(max(lower_bound, 0.0) / 0.005) * 0.005
    return round(max(MATERIAL_FLOOR, calibrated), 4)


def preregister(name: str = "location", classes: int = head.CLASSES) -> dict:
    """Build the bar. Run before training; the file it writes is the bar."""
    import numpy

    rows = [row for row in tile_module.read_locations() if row["side"] == "eval"]
    rows.sort(key=lambda row: row["location_id"])
    control = extract()
    covered = [row for row in rows if row["location_id"] in control]
    if len(covered) != len(rows):
        raise ValueError(
            f"the incumbent has committed scores for {len(covered)} of {len(rows)} evaluation "
            "locations. A bar quoted against a yardstick that does not cover the population is "
            "a bar about a different population."
        )

    labels = numpy.array([row["score"] for row in covered])
    populations = {}
    for row in covered:
        populations.setdefault(control[row["location_id"]]["population"], []).append(row)

    vendored = vendor({row["location_id"]: control[row["location_id"]] for row in covered}, name)
    stick = yardstick(covered, control, classes)
    precision = seed_precision(covered, control, classes)
    gates = {}
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        gates[label] = {
            "gated": index in (1, 2),
            "margin": margin_of(precision[label]["widest_lower_bound"]),
            "positives": stick["cutpoints"][label]["positives"],
        }

    return {
        "schema": SCHEMA,
        "head": name,
        "yardstick_record": vendored.name,
        "question": (
            "Is a location head trained inside this repository approximately comparable to the "
            "one the source project deployed, within the variance a fresh seed and a fresh "
            "rendering pipeline produce?"
        ),
        "population": {
            "rule": (
                "every location on the evaluation side of BOTH projects, joined on the "
                "c-inclusive location coordinate"
            ),
            "locations": len(covered),
            "clusters": len({row["group"] for row in covered}),
            "labels": {str(score): int((labels == score).sum()) for score in range(1, classes + 1)},
            "base_rates": {
                head.cutpoint_label(index): float((labels >= index + 2).mean())
                for index in range(classes - 1)
            },
            "incumbent_population": {key: len(value) for key, value in sorted(populations.items())},
            "declared": [
                "Not a same-input comparison: each head is scored through its own deploy view "
                "of the same location, so two pipelines are compared against one set of human "
                "verdicts.",
                f"{len(populations.get('selection', []))} of {len(covered)} locations were the "
                "incumbent's own checkpoint-selection population. The yardstick is therefore "
                "generous to the incumbent, most at the first cutpoint.",
                f"The {len(populations.get('primary', []))} locations that were clean on both "
                "sides are reported and are NOT a decision surface: they hold too few "
                "positives to resolve anything.",
                "Both sides are read as unconditional probabilities — the running product of "
                "the conditional cutpoints — so neither is advantaged by the reading.",
            ],
        },
        "yardstick": stick,
        "seed_precision": precision,
        "rules": {
            "statistic": (
                "paired difference in AUC against each incumbent seed on the same locations, "
                "with a 95% cluster bootstrap resampling whole location groups"
            ),
            "draws": DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "margin": (
                "the larger of a 0.02 floor and the lowest bound any PAIR of the incumbent's "
                "own three seeds produces on this population under this same statistic, "
                "rounded up to half a point of AUC. The floor is there because a fresh "
                "rendering pipeline is a bigger perturbation than a fresh seed; the calibrated "
                "term is there because a bar the incumbent's own seeds fail against each other "
                "is not a bar about the candidate. Checked: `tests/test_acceptance.py` hands "
                "the read one of the yardstick's own seeds and requires ACCEPT."
            ),
            "verdicts": {
                "PASS": "the lower bound of the paired interval is above minus the margin, "
                "against all three incumbent seeds",
                "FAIL": "the upper bound is below minus the margin against any seed",
                "BORDERLINE": "anything else — the interval straddles the margin",
            },
            "escalation": (
                "a BORDERLINE gate is re-read with three seeds of this head, using the median "
                "seed by that arm's own statistic. The median, not the best: picking the best "
                "of three is the thing pre-registration exists to stop."
            ),
            "min_positives": MIN_POSITIVES,
            "not_called": NOT_CALLED,
        },
        "arms": {
            "ordering": gates,
            "interface": {
                "gated": True,
                "rule": (
                    "the checkpoint emits K-1 cutpoints and the score file carries a "
                    "probability for every one of them, non-increasing along the row. The "
                    "supply engine's tenfold class-4 weighting reads P(>=4) directly, so a "
                    "head that exposed only a rank score would not be usable at all."
                ),
            },
            "calibration": {
                "gated": True,
                "rule": (
                    "the mean predicted rate at each gated cutpoint, over the population, "
                    "within a factor of two of the observed base rate"
                ),
                "tolerance": [0.5, 2.0],
                "incumbent": {
                    head.cutpoint_label(index): {
                        arm: float(
                            numpy.mean([control[row["location_id"]][arm][index] for row in covered])
                            / max((labels >= index + 2).mean(), 1e-12)
                        )
                        for arm in INCUMBENT_ARMS
                    }
                    for index in (1, 2)
                },
            },
            "per_partition": {
                "gated": False,
                "rule": (
                    f"reported where a partition holds at least {MIN_POSITIVES} positives at "
                    "that cutpoint, and NOT_MEASURABLE with its count otherwise. Never a gate: "
                    "these slices are between zero and twenty-four positives wide."
                ),
            },
        },
    }


def read(name: str = "location", classes: int = head.CLASSES) -> dict:
    """Read a trained head's scores against the bar. The bar comes from the file."""
    import numpy

    from fractal_wallpapers.models import scoring

    bar = json.loads(prereg_path(name).read_text(encoding="utf-8"))
    scored = {int(row["location_id"]): row for row in scoring.read(name=name)}
    control = incumbent(name)
    rows = [row for row in tile_module.read_locations() if row["side"] == "eval"]
    rows.sort(key=lambda row: row["location_id"])
    covered = [
        row for row in rows if row["location_id"] in control and row["location_id"] in scored
    ]
    if len(covered) != bar["population"]["locations"]:
        raise ValueError(
            f"the read covers {len(covered)} locations, the bar was written for "
            f"{bar['population']['locations']}. A bar and a read over different populations "
            "are two statements about two things."
        )

    labels = numpy.array([row["score"] for row in covered])
    groups = numpy.array([row["group"] for row in covered])
    ours = {
        index: numpy.array(
            [scored[row["location_id"]][f"p_{head.cutpoint_label(index)}"] for row in covered]
        )
        for index in range(classes - 1)
    }

    arms, verdicts = {}, []
    for index in range(classes - 1):
        label = head.cutpoint_label(index)
        gate = bar["arms"]["ordering"][label]
        truth = (labels >= index + 2).astype(int)
        ours_auc = metrics.auc(truth, ours[index])
        against = {}
        for arm in INCUMBENT_ARMS:
            theirs = numpy.array([control[row["location_id"]][arm][index] for row in covered])
            delta = metrics.paired_delta(
                truth, ours[index], theirs, groups, draws=DRAWS, seed=BOOTSTRAP_SEED
            )
            margin = gate["margin"]
            if delta["lo"] is None:
                call = "NOT_MEASURABLE"
            elif delta["lo"] > -margin:
                call = "PASS"
            elif delta["hi"] < -margin:
                call = "FAIL"
            else:
                call = "BORDERLINE"
            against[arm] = {
                "ours": delta["ours"],
                "theirs": delta["theirs"],
                "delta": delta["delta"],
                "ci": [delta["lo"], delta["hi"]],
                "verdict": call,
            }
        calls = {entry["verdict"] for entry in against.values()}
        verdict = (
            "FAIL"
            if "FAIL" in calls
            else ("PASS" if calls == {"PASS"} else "BORDERLINE" if calls else "NOT_MEASURABLE")
        )
        arms[label] = {
            "gated": gate["gated"],
            "margin": gate["margin"],
            "positives": int(truth.sum()),
            "ours": ours_auc,
            "incumbent_band": bar["yardstick"]["cutpoints"][label]["band"],
            "against": against,
            "verdict": verdict,
        }
        if gate["gated"]:
            verdicts.append(verdict)

    interface = _interface_arm(scored, classes)
    calibration = _calibration_arm(bar, labels, ours, classes)
    verdicts.extend([interface["verdict"], calibration["verdict"]])

    return {
        "schema": SCHEMA,
        "head": name,
        "prereg": str(prereg_path(name)),
        "population": {
            "locations": len(covered),
            "clusters": int(len(set(groups.tolist()))),
            "positives": {
                head.cutpoint_label(index): int((labels >= index + 2).sum())
                for index in range(classes - 1)
            },
        },
        "ordering": arms,
        "interface": interface,
        "calibration": calibration,
        "per_partition": _partition_arm(covered, labels, ours, control, classes),
        "clean_subset": _clean_subset(covered, control, ours, labels, classes),
        "verdict": (
            "FAIL"
            if "FAIL" in verdicts
            else ("ACCEPT" if set(verdicts) == {"PASS"} else "BORDERLINE")
        ),
    }


def _interface_arm(scored: dict, classes: int) -> dict:
    """Every cutpoint present on every row, and never out of order."""
    columns = [f"p_{head.cutpoint_label(index)}" for index in range(classes - 1)]
    missing = [
        identifier
        for identifier, row in scored.items()
        if any(column not in row for column in columns)
    ]
    inverted = [
        identifier
        for identifier, row in scored.items()
        if not missing
        and any(
            row[columns[index + 1]] > row[columns[index]] + 1e-12
            for index in range(len(columns) - 1)
        )
    ]
    return {
        "cutpoints": columns,
        "rows": len(scored),
        "rows_missing_a_cutpoint": len(missing),
        "rows_out_of_order": len(inverted),
        "verdict": "PASS" if not missing and not inverted else "FAIL",
    }


def _calibration_arm(bar: dict, labels, ours: dict, classes: int) -> dict:
    import numpy

    low, high = bar["arms"]["calibration"]["tolerance"]
    out, verdict = {}, "PASS"
    for index in range(1, classes - 1):
        label = head.cutpoint_label(index)
        observed = float((labels >= index + 2).mean())
        predicted = float(numpy.mean(ours[index]))
        ratio = predicted / max(observed, 1e-12)
        inside = low <= ratio <= high
        if not inside:
            verdict = "FAIL"
        out[label] = {
            "observed": observed,
            "predicted": predicted,
            "ratio": ratio,
            "inside": inside,
            "incumbent_ratio": bar["arms"]["calibration"]["incumbent"][label],
        }
    return {"tolerance": [low, high], "cutpoints": out, "verdict": verdict}


def _partition_arm(covered: list[dict], labels, ours: dict, control: dict, classes: int) -> dict:
    import numpy

    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    out = {}
    for partition in ALL_PARTITIONS:
        picked = [index for index, row in enumerate(covered) if row["partition"] == partition]
        entry: dict = {"locations": len(picked)}
        for index in range(1, classes - 1):
            label = head.cutpoint_label(index)
            if not picked:
                entry[label] = {"verdict": "NOT_MEASURABLE", "why": "no evaluation rows"}
                continue
            truth = (labels[picked] >= index + 2).astype(int)
            positives = int(truth.sum())
            if positives < MIN_POSITIVES:
                entry[label] = {
                    "verdict": "NOT_MEASURABLE",
                    "positives": positives,
                    "why": f"below the {MIN_POSITIVES}-positive rule",
                }
                continue
            mine = metrics.auc(truth, ours[index][picked])
            theirs = {
                arm: metrics.auc(
                    truth,
                    numpy.array([control[covered[i]["location_id"]][arm][index] for i in picked]),
                )
                for arm in INCUMBENT_ARMS
            }
            entry[label] = {
                "verdict": "REPORTED",
                "positives": positives,
                "ours": mine,
                "incumbent": theirs,
            }
        out[partition] = entry
    return out


def _clean_subset(covered, control, ours, labels, classes: int) -> dict:
    """The locations neither project's checkpoint pick ever touched.

    Reported because it is the only fully clean comparison available, and framed
    as not-a-decision because it holds too few positives to be one.
    """
    import numpy

    picked = [
        index
        for index, row in enumerate(covered)
        if control[row["location_id"]]["population"] == "primary"
    ]
    out = {
        "locations": len(picked),
        "why_not_a_decision": (
            "clean on both sides, and far too thin: the wallpaper cutpoint has a handful of "
            "positives here and the release cutpoint has none. Reported so the reader can see "
            "the cost of the contamination the primary population declares."
        ),
    }
    for index in range(1, classes - 1):
        label = head.cutpoint_label(index)
        truth = (labels[picked] >= index + 2).astype(int)
        positives = int(truth.sum())
        if positives < MIN_POSITIVES:
            out[label] = {"positives": positives, "verdict": "NOT_MEASURABLE"}
            continue
        out[label] = {
            "positives": positives,
            "ours": metrics.auc(truth, ours[index][picked]),
            "incumbent": {
                arm: metrics.auc(
                    truth,
                    numpy.array([control[covered[i]["location_id"]][arm][index] for i in picked]),
                )
                for arm in INCUMBENT_ARMS
            },
        }
    return out


__all__ = [
    "DRAWS",
    "beside",
    "INCUMBENT_ARMS",
    "MATERIAL_FLOOR",
    "MIN_POSITIVES",
    "NOT_CALLED",
    "SCHEMA",
    "acceptance_path",
    "extract",
    "incumbent",
    "margin_of",
    "prereg_path",
    "preregister",
    "read",
    "seed_precision",
    "vendor",
    "yardstick",
    "yardstick_path",
]
