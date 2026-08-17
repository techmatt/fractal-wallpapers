"""The bar each finished-render judge has to clear, written before it exists.

## Why the file comes first

A bar chosen after the numbers are in is not a bar. So the pre-registration is
its own record, written and committed before either trainer runs, and this module
does two things that never happen in one step: [`preregister`] builds the bar out
of the source project's committed figures and the sheet's own resolving power,
and [`read`] takes a trained head's scores and reports what the bar says. The bar
is loaded from the file; nothing in the read may invent one.

## One sheet each, and it is the only honest surface there is

Every other batch in these corpora served a head's own verdict prefilled, so a
rate measured on one is a statement about agreement with that head. Two sheets
were served blind, they were bought precisely to referee two heads without that
coupling, and they are the whole evaluation side:

```text
smooth_render   blind_minibrot  197 rows   live boundary >=4   96 positives
strange_render  blind_modes     150 rows   live boundary >=2   76 positives
```

Each sheet informs **exactly one boundary**, decided when it was drawn rather
than after. Sheet D holds six rows below tier 3 in 197, so its >=3 boundary is
barely measurable and its >=2 boundary does not exist at all; sheet E holds six
rows at tier 3 in 150, so the reverse. Both are read at their own boundary, both
are reported at the other, and only the live one gates.

## Three things declared before any number exists

**It is not a same-input comparison, and it is further from one than the location
head's was.** The yardstick figures were measured on the source project's own
JPEGs of these sheets. This head is scored on pictures regenerated here from the
recipes those rows carry, through a different renderer and a different colormap
library. Two whole pipelines are compared against one set of human verdicts. That
is the comparison available, and the gap is wider here than it was there because
the coloring recipe — gamma, traversal, fold, transfer — is being reproduced from
a record rather than shared.

**The adopted head's figure on sheet D is a selected maximum.** Its adoption
record says so outright: five seeds were trained and the one with the best sheet-D
AUC at the live boundary was picked, which spends the instrument and leaves the
picked number un-held-out. So the bar is set against the **band's centre**, not
against the picked seed, and the whole band is reported beside it. On sheet E no
seed band was ever committed, so its figure may carry the same selection and
cannot be corrected for; that is declared instead.

**Nothing small is called.** Sheet E's own paired interval between the incumbent
and the adopted head spans 0.126 of AUC at its live boundary — the population
cannot resolve a difference smaller than about six points. Sheet D's yardstick
moves 0.096 across five seeds of one recipe. Differences inside those are
reported as bands and are not called in either direction.

## What gates and what is only reported

Ordering at the live boundary gates. So do the interface — every cutpoint present
and never out of order — and calibration within a factor of two. **Decoded-verdict
agreement is reported and does not gate**: no decoded verdict for either source
head on either sheet was ever committed, so there is nothing to compare ours
against, and a number with no yardstick cannot be a bar.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import metrics
from fractal_wallpapers.models.head import decode

#: The schema the pre-registration, the yardstick and the read all carry.
SCHEMA = 1

#: Draws in the cluster bootstrap, and its seed.
DRAWS, BOOTSTRAP_SEED = 5000, 0

#: The floor on "materially worse", in AUC. Below this a difference is inside
#: what a fresh seed and a fresh rendering pipeline move on their own.
MATERIAL_FLOOR = 0.02

#: What each judge is read on. `boundary` is the tier the sheet was drawn to
#: inform, decided before the draw; `classes` is how many tiers the checkpoints
#: being compared emit, which is what decides how many cutpoints there are to read
#: — a fact about the models on both sides of the comparison, not about the store,
#: which is cast on [`finished.SCALE`].
SHEETS = {
    "smooth_render": {
        "batch": "blind_minibrot",
        "boundary": 4,
        "classes": 4,
        "source_batch": "2026-08-11_wallpaper_blind_minibrot_v1",
    },
    "strange_render": {
        "batch": "blind_modes",
        "boundary": 2,
        "classes": 3,
        "source_batch": "2026-08-11_render_mode_blind_v1",
    },
}

#: Where the source project's committed readings of these two sheets live, and
#: which head each names. Read-only, outside this repository, and read exactly
#: once — when the bar is written — because the figures are vendored.
SOURCE_RECORDS = {
    "smooth_render": {
        "reverdict": Path("data/wallpaper_head/sheet_d_reverdict/report.json"),
        "adoption": Path("data/wallpaper_head/v4b/adoption_record.json"),
        "incumbent": "v3",
        "adopted": "v4b",
        "slice": "blind_minibrot",
    },
    "strange_render": {
        "reverdict": Path("data/render_mode_head/sheet_e_reverdict/report.json"),
        "adoption": Path("data/render_mode_head/v3/adoption_record.json"),
        "incumbent": "v1",
        "adopted": "v3",
        "slice": "pooled",
    },
}


class AcceptanceError(RuntimeError):
    """The bar cannot be built, or a read cannot be made against it."""


def head_dir(head: str, run: str | None = None) -> Path:
    from fractal_wallpapers.paths import repo_root

    base = repo_root() / "models" / finished.head_of(head)
    return base / run if run else base


def prereg_path(head: str) -> Path:
    return head_dir(head) / "prereg.json"


def yardstick_path(head: str) -> Path:
    """The source's committed figures for this sheet, vendored.

    Tracked, and that is the point: the source project is a sibling checkout
    during the build era and gone afterwards. A bar whose yardstick lives in
    another repository is a bar nobody can re-read.
    """
    return head_dir(head) / "yardstick.json"


def acceptance_path(head: str) -> Path:
    return head_dir(head) / "acceptance.json"


def boundary_label(boundary: int) -> str:
    return f"ge{boundary}"


def extract(head: str, root: Path) -> dict:
    """The source's committed reading of one sheet, in one shape for both heads.

    The two reports were written by different tools and are shaped differently —
    one carries a per-seed band, the other a paired interval against the head it
    replaced — so each is read on its own terms and folded into the same record
    here. Nothing is computed: every number below is copied.
    """
    head = finished.head_of(head)
    where = SOURCE_RECORDS[head]
    report_path = Path(root) / where["reverdict"]
    if not report_path.is_file():
        raise AcceptanceError(
            f"{report_path} is missing. It is the source project's own reading of this "
            f"sheet, and it is the only yardstick that exists for it."
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    adoption = json.loads((Path(root) / where["adoption"]).read_text(encoding="utf-8"))
    boundary = boundary_label(SHEETS[head]["boundary"])

    if head == "smooth_render":
        cell = report["motivating"]["blind_minibrot"]
        band = [entry[f"auc_{boundary}"] for entry in report["v4b_seed_band"]["per_seed"]]
        incumbent = {"auc": cell["v3"][f"auc_{boundary}"], "ap": cell["v3"][f"ap_{boundary}"]}
        # Three different numbers wear this head's name on this sheet, and
        # conflating them would misstate the bar. `auc` is the checkpoint its own
        # trainer staged, chosen on its pooled evaluation side and NOT on this
        # sheet — the closest thing to a held-out figure that exists. `picked` is
        # the seed the adoption then chose *by this sheet's own statistic*, which
        # is a selected maximum. The band is all five.
        adopted = {
            "auc": cell["v4b"][f"auc_{boundary}"],
            "ap": cell["v4b"][f"ap_{boundary}"],
            "auc_is": "the seed its own trainer staged, chosen on its pooled evaluation "
            "side rather than on this sheet",
            "picked": max(band),
            "picked_is": "the seed the adoption chose BY THIS SHEET'S OWN statistic — a "
            "selected maximum, which its adoption record says outright",
            "seeds": band,
            "picked_from": len(band),
            "selected": True,
        }
        # The population's own resolving power: how far one recipe's seeds move
        # on this very sheet. It is the control comparison that exists here.
        resolution = {
            "kind": "seed band",
            "what": (
                "five seeds of the adopted recipe, scored on this sheet. The spread is what "
                "the seed alone is worth, and a candidate has to survive the bottom of it."
            ),
            "lower_reach": max(band) - min(band) if band else None,
            "below_centre": (sum(band) / len(band)) - min(band) if band else None,
        }
        tiers = report["slice"]["tiers"]
    else:
        pooled = report["arms"]["v3"]["pooled"][f"auc_{boundary}"]
        interval = pooled["delta_ci"]
        incumbent = {
            "auc": pooled["v1"],
            "ap": report["arms"]["v3"]["pooled"][f"ap_{boundary}"]["v1"],
        }
        adopted = {
            "auc": pooled["arm"],
            "ap": report["arms"]["v3"]["pooled"][f"ap_{boundary}"]["arm"],
            "seeds": None,
            "picked_from": None,
            "selected": None,
        }
        resolution = {
            "kind": "paired interval",
            "what": (
                "the source's own paired bootstrap between the head it replaced and the one "
                "it adopted, on this sheet. No seed band was ever committed for it, so this "
                "is the control comparison available: the interval's lower reach is how far "
                "down a difference that changed nothing was still able to go."
            ),
            "lower_reach": abs(interval["lo"]),
            "below_centre": abs(interval["lo"]),
            "interval": [interval["lo"], interval["hi"]],
        }
        tiers = report["slice"]["tiers"]

    return {
        "schema": SCHEMA,
        "head": head,
        "boundary": boundary,
        "source": {
            "reverdict": where["reverdict"].as_posix(),
            "adoption": where["adoption"].as_posix(),
            "generated": report.get("generated"),
            "adopted_on": adoption.get("adopted_on"),
        },
        "population": {
            "rows": report["slice"]["n"],
            "tiers": {key: int(value) for key, value in tiers["hist"].items()},
        },
        "incumbent": {"name": where["incumbent"], **incumbent},
        "adopted": {"name": where["adopted"], **adopted},
        "resolution": resolution,
        "declared_by_the_source": adoption.get("not_established", []),
    }


def vendor(head: str, root: Path) -> Path:
    """Copy the source's figures in, once, and return where they landed."""
    document = extract(head, root)
    path = yardstick_path(head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def yardstick(head: str) -> dict:
    path = yardstick_path(head)
    if not path.is_file():
        raise AcceptanceError(
            f"{path} is missing. It is written when the bar is, from the source project's "
            f"committed reading of this sheet; without it there is nothing to compare to."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise AcceptanceError(f"{path}: schema {document.get('schema')!r}, expected {SCHEMA}")
    return document


def margin_of(lower_reach: float | None) -> float:
    """The margin at the live boundary: the floor, or what the control needs.

    Calibrated on the **lower reach** of the control comparison rather than on
    its width. Two readings of one recipe can sit apart *and* be measured
    imprecisely, and a candidate has to survive both — which is the correction
    the location head's bar needed after it could not pass its own control.
    Rounded up to half a point of AUC, so the number in the record is a decision
    rather than the tail of a bootstrap.
    """
    calibrated = math.ceil(max(lower_reach or 0.0, 0.0) / 0.005) * 0.005
    return round(max(MATERIAL_FLOOR, calibrated), 4)


def population(head: str) -> list[dict]:
    """The sheet, as this repository holds it: one row per blind picture."""
    head = finished.head_of(head)
    batch = SHEETS[head]["batch"]
    rows = [row for row in finished.resolved(head).scored() if row["batch"] == batch]
    if not rows:
        raise AcceptanceError(
            f"the {head} store holds no rows of {batch!r}. That sheet is the whole "
            f"evaluation side, so there is nothing to judge against."
        )
    rows.sort(key=lambda row: repr(finished.render_key(row)))
    return rows


def preregister(head: str, root: Path) -> dict:
    """Build the bar. Run before training; the file it writes is the bar."""
    head = finished.head_of(head)
    sheet = SHEETS[head]
    boundary = sheet["boundary"]
    label = boundary_label(boundary)
    vendored = vendor(head, root)
    stick = yardstick(head)
    rows = population(head)

    tiers = {
        str(tier): sum(1 for row in rows if row["score"] == tier) for tier in finished.tiers(head)
    }
    theirs = {key: int(value) for key, value in stick["population"]["tiers"].items() if int(value)}
    ours = {key: value for key, value in tiers.items() if value}
    if len(rows) != stick["population"]["rows"] or ours != theirs:
        raise AcceptanceError(
            f"this repository holds {len(rows)} rows of the sheet with tiers {ours}; the "
            f"source's committed reading covers {stick['population']['rows']} with {theirs}. "
            f"A bar quoted against a yardstick measured on a different population is a bar "
            f"about something else."
        )

    margin = margin_of(stick["resolution"]["below_centre"])
    target = (
        sum(stick["adopted"]["seeds"]) / len(stick["adopted"]["seeds"])
        if stick["adopted"]["seeds"]
        else stick["adopted"]["auc"]
    )
    positives = sum(1 for row in rows if row["score"] >= boundary)

    return {
        "schema": SCHEMA,
        "head": head,
        "yardstick_record": vendored.name,
        "question": (
            f"Is a {head} judge trained inside this repository approximately comparable to the "
            f"one the source project adopted, read on the same blind sheet at the boundary "
            f"that sheet was drawn to inform, within the variance a fresh seed and a fresh "
            f"rendering pipeline produce?"
        ),
        "population": {
            "batch": sheet["batch"],
            "source_batch": sheet["source_batch"],
            "rows": len(rows),
            "locations": len({finished.place_of(row) for row in rows}),
            "tiers": tiers,
            "boundary": label,
            "positives": positives,
            "base_rate": positives / len(rows),
            "blind": (
                "no suggestion was prefilled and no score ordered the page, which is the "
                "whole reason this sheet is the evaluation side"
            ),
        },
        "declared": [
            "NOT A SAME-INPUT COMPARISON, and further from one than the location head's was: "
            "the yardstick was measured on the source project's own pictures of these rows, "
            "and this head is scored on pictures regenerated here from the recipes the rows "
            "carry, through a different renderer and a different colormap library.",
            (
                "THE TARGET IS THE BAND'S CENTRE. Three numbers wear the adopted head's name "
                f"on this sheet: {stick['adopted']['picked']:.4f}, the seed the adoption chose "
                "by this sheet's own statistic, which its own record calls a selected maximum; "
                f"{stick['adopted']['auc']:.4f}, the seed its trainer staged on its pooled "
                f"evaluation side instead; and {target:.4f}, the centre of all "
                f"{stick['adopted']['picked_from']}. The last is what the bar is set against, "
                "and the other two are reported beside it."
            )
            if stick["adopted"]["seeds"]
            else (
                "NO SEED BAND WAS EVER COMMITTED for the adopted head on this sheet, so its "
                f"figure of {stick['adopted']['auc']:.4f} may carry the same selection the "
                "other sheet's does and cannot be corrected for. It is used as written."
            ),
            f"ONE BOUNDARY. This sheet holds {tiers} on a 1..{sheet['classes']} scale, so only "
            f"{label} is measurable on it with both classes present in quantity. The other "
            f"boundaries are reported where they exist and gate nothing.",
            "DECODED-VERDICT AGREEMENT DOES NOT GATE: no decoded verdict for either source "
            "head on either sheet was committed, so there is nothing to compare ours against.",
        ],
        "yardstick": {
            "incumbent": stick["incumbent"],
            "adopted": stick["adopted"],
            "target": target,
            "target_rule": (
                "the mean of the adopted head's seed band on this sheet"
                if stick["adopted"]["seeds"]
                else "the adopted head's committed figure, there being no band"
            ),
            "resolution": stick["resolution"],
        },
        "rules": {
            "statistic": (
                f"AUC at {label}, with a 95% cluster bootstrap resampling whole locations — "
                "a location contributes several pictures to these sheets and they are not "
                "independent"
            ),
            "draws": DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "margin": margin,
            "margin_rule": (
                f"the larger of a {MATERIAL_FLOOR} floor and how far below its own centre the "
                f"source's control comparison on this sheet reaches "
                f"({stick['resolution']['kind']}: "
                f"{stick['resolution']['below_centre']:.4f}), rounded up to half a point of "
                "AUC. Calibrated on the LOWER REACH rather than on the width, because two "
                "readings of one recipe can sit apart and be measured imprecisely and a "
                "candidate has to survive both."
            ),
            "verdicts": {
                "PASS": "the lower bound of our interval is above the target minus the margin",
                "FAIL": "the upper bound is below the target minus the margin",
                "BORDERLINE": "anything else — the interval straddles it",
            },
            "escalation": (
                "a BORDERLINE read buys three seeds of this head, and the boundary is then "
                "judged on the MEDIAN seed by its own statistic. The median, not the best: "
                "picking the best of three is the thing pre-registration exists to stop."
            ),
            "not_called": (
                "a difference smaller than the margin is reported as a band and is not called "
                "in either direction. Label noise at these boundaries is larger than it is."
            ),
        },
        "arms": {
            "ordering": {
                "gated": True,
                "boundary": label,
                "target": target,
                "margin": margin,
                "positives": positives,
            },
            "interface": {
                "gated": True,
                "rule": (
                    f"the checkpoint emits {sheet['classes'] - 1} cutpoints and the score file "
                    "carries a probability for every one of them, non-increasing along the row"
                ),
            },
            "calibration": {
                "gated": True,
                "rule": (
                    f"the mean predicted rate at {label}, over the sheet, within a factor of "
                    "two of the observed base rate"
                ),
                "tolerance": [0.5, 2.0],
            },
            "agreement": {
                "gated": False,
                "rule": (
                    "the share of rows whose decoded tier equals the human one, decoded as "
                    "1 + the number of cutpoints whose unconditional probability reaches a "
                    "half. Reported with its own interval; nothing to compare it to."
                ),
            },
            "other_boundaries": {
                "gated": False,
                "rule": (
                    "reported where both classes are present, and NOT_MEASURABLE with the "
                    "count otherwise. This sheet was drawn to inform one boundary."
                ),
            },
        },
    }


def read(head: str, runs: list[str | None] | None = None) -> dict:
    """Read this head's scores against the bar. The bar comes from the file."""
    import numpy

    from fractal_wallpapers.models import finished_scoring

    head = finished.head_of(head)
    # An empty name is the head's own run, not a run called "". The two reach
    # the same directory either way; normalizing here keeps the record readable.
    runs = [None] if runs is None else [run or None for run in runs]
    bar = json.loads(prereg_path(head).read_text(encoding="utf-8"))
    sheet = SHEETS[head]
    boundary, label = sheet["boundary"], boundary_label(sheet["boundary"])
    cutpoints = sheet["classes"] - 1

    rows = population(head)
    by_run = {
        run: {row["name"]: row for row in finished_scoring.read(head=head, run=run)} for run in runs
    }
    from fractal_wallpapers.models import renders

    names = [renders.job_name({**row, "_head": head}) for row in rows]
    scored = by_run[runs[0]]
    covered = [(row, name) for row, name in zip(rows, names, strict=True) if name in scored]
    if len(covered) != bar["population"]["rows"]:
        raise AcceptanceError(
            f"the read covers {len(covered)} rows, the bar was written for "
            f"{bar['population']['rows']}. A bar and a read over different populations are "
            f"two statements about two things."
        )

    labels = numpy.array([row["score"] for row, _ in covered])
    groups = numpy.array([repr(finished.place_of(row)) for row, _ in covered])

    def column(run, index):
        table = by_run[run]
        return numpy.array([table[name][f"p_ge{index + 2}"] for _, name in covered])

    truth = (labels >= boundary).astype(int)
    index = boundary - 2

    def named(run):
        return run if run else "its own"

    band = {named(run): metrics.auc(truth, column(run, index)) for run in runs}
    ranked = sorted(runs, key=lambda run: band[named(run)] or 0.0)
    judged = ranked[len(ranked) // 2]
    ours = column(judged, index)

    interval = metrics.bootstrap(
        lambda picked: metrics.auc(truth[picked], ours[picked]),
        groups,
        draws=DRAWS,
        seed=BOOTSTRAP_SEED,
    )
    target = bar["arms"]["ordering"]["target"]
    margin = bar["arms"]["ordering"]["margin"]
    floor = target - margin
    if interval["lo"] is None:
        ordering_verdict = "NOT_MEASURABLE"
    elif interval["lo"] > floor:
        ordering_verdict = "PASS"
    elif interval["hi"] < floor:
        ordering_verdict = "FAIL"
    else:
        ordering_verdict = "BORDERLINE"

    interface = _interface_arm(scored, cutpoints)
    calibration = _calibration_arm(truth, ours, bar)
    agreement = _agreement_arm(labels, [column(judged, i) for i in range(cutpoints)], groups)
    verdicts = [ordering_verdict, interface["verdict"], calibration["verdict"]]

    return {
        "schema": SCHEMA,
        "head": head,
        "prereg": str(prereg_path(head)),
        "runs": [run if run else "its own" for run in runs],
        "population": {
            "rows": len(covered),
            "locations": int(len(set(groups.tolist()))),
            "boundary": label,
            "positives": int(truth.sum()),
        },
        "ordering": {
            "boundary": label,
            "ours": metrics.auc(truth, ours),
            "our_band": band,
            "judged_on": named(judged),
            "interval": [interval["lo"], interval["hi"]],
            "target": target,
            "margin": margin,
            "floor": floor,
            "incumbent": bar["yardstick"]["incumbent"],
            "adopted": bar["yardstick"]["adopted"],
            "verdict": ordering_verdict,
        },
        "interface": interface,
        "calibration": calibration,
        "agreement": agreement,
        "other_boundaries": _other_boundaries(labels, by_run, judged, covered, cutpoints, boundary),
        "verdict": (
            "FAIL"
            if "FAIL" in verdicts
            else ("ACCEPT" if set(verdicts) == {"PASS"} else "BORDERLINE")
        ),
    }


def _interface_arm(scored: dict, cutpoints: int) -> dict:
    columns = [f"p_ge{index + 2}" for index in range(cutpoints)]
    missing = [name for name, row in scored.items() if any(c not in row for c in columns)]
    inverted = [
        name
        for name, row in scored.items()
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


def _calibration_arm(truth, ours, bar: dict) -> dict:
    import numpy

    low, high = bar["arms"]["calibration"]["tolerance"]
    observed = float(truth.mean())
    predicted = float(numpy.mean(ours))
    ratio = predicted / max(observed, 1e-12)
    inside = low <= ratio <= high
    return {
        "tolerance": [low, high],
        "observed": observed,
        "predicted": predicted,
        "ratio": ratio,
        "verdict": "PASS" if inside else "FAIL",
    }


def _agreement_arm(labels, columns, groups) -> dict:
    import numpy

    stacked = numpy.stack(columns, axis=1)
    decoded = numpy.array([decode(row, stacked.shape[1]) for row in stacked])
    matched = (decoded == labels).astype(float)
    interval = metrics.bootstrap(
        lambda picked: float(matched[picked].mean()), groups, draws=DRAWS, seed=BOOTSTRAP_SEED
    )
    return {
        "agreement": float(matched.mean()),
        "interval": [interval["lo"], interval["hi"]],
        "within_one_tier": float((numpy.abs(decoded - labels) <= 1).mean()),
        "decoded_tiers": {
            str(tier): int((decoded == tier).sum()) for tier in sorted(set(decoded.tolist()))
        },
        "verdict": "REPORTED",
        "why_not_gated": (
            "no decoded verdict for either source head on this sheet was committed, so there "
            "is nothing to compare this to"
        ),
    }


def _other_boundaries(labels, by_run, judged, covered, cutpoints: int, live: int) -> dict:
    import numpy

    out = {}
    for index in range(cutpoints):
        tier = index + 2
        if tier == live:
            continue
        truth = (labels >= tier).astype(int)
        positives = int(truth.sum())
        negatives = len(truth) - positives
        if positives == 0 or negatives == 0:
            out[f"ge{tier}"] = {
                "verdict": "NOT_MEASURABLE",
                "positives": positives,
                "negatives": negatives,
                "why": "one class only",
            }
            continue
        table = by_run[judged]
        column = numpy.array([table[name][f"p_ge{tier}"] for _, name in covered])
        out[f"ge{tier}"] = {
            "verdict": "REPORTED",
            "positives": positives,
            "negatives": negatives,
            "ours": metrics.auc(truth, column),
        }
    return out


__all__ = [
    "BOOTSTRAP_SEED",
    "DRAWS",
    "MATERIAL_FLOOR",
    "SCHEMA",
    "SHEETS",
    "SOURCE_RECORDS",
    "AcceptanceError",
    "acceptance_path",
    "boundary_label",
    "decode",
    "extract",
    "head_dir",
    "margin_of",
    "population",
    "prereg_path",
    "preregister",
    "read",
    "vendor",
    "yardstick",
    "yardstick_path",
]
