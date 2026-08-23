"""Where a finished-render head's release floor sits, measured off the labels.

A release floor answers one question: **above what score does this head stop
disagreeing with the people who judged its corpus?** It is not the natural
cutpoint of a probability scale and it is not a policy — it is a crossing, and
this module is the command that finds it.

It exists because the crossing that set `curation.floors.STRANGE_RELEASE_BAR` to
0.685 was never committed. It lived as four sentences of prose inside the bar's
own `method` string; `grep -rn isotonic` reached one assertion in the suite and
nothing else. A number that cannot be re-derived is a number that cannot be
*checked*, and a bar nobody can check is the thing this project's whole cut
discipline was written to avoid.

## The fit

For every labeled picture in the head's store, two numbers: what the head says
(`P(≥3)` through the **shipped** artifact, which is the scale every curation
decision is taken on) and what the person said (`1` if they scored it 3 or more,
`0` otherwise). Fit `P(rated ≥3 | score)` as a **monotone non-decreasing** step
function of the score — pool-adjacent-violators, ties pooled — and read off the
lowest score whose fitted value reaches a half. Below that crossing the head and
the labels disagree more often than they agree; above it they do not.

Monotone rather than parametric because the only thing anybody is willing to
assume about a judge is that a higher score does not mean a worse picture. PAVA
is the whole of it and it is fifteen lines: no dependency, no smoothing
parameter, nothing to tune, and the same answer every time.

## The roundings go up, because a floor is a floor

The crossing is rounded **up** to three places. That direction is not neutral: a
floor rounded down admits material the fit did not vouch for, and the whole point
of a floor is that everything under it is out. The historical strange bar was
rounded up to the next 0.005 instead, which is a coarser grid and lands higher;
[`fit`] reports both so a restatement can be compared against the number it is
restating rather than against a differently-rounded cousin.

## What is hashed, and why

A floor is only as re-derivable as its inputs, so the record carries the sha256
of the two of them: the label store's rows as the store resolves them, and the
scores this pass read. Neither is tracked at full size — the pictures are
regenerated from the rows and the scores are a function of the artifact — so the
hashes are what say *these* rows and *that* artifact produced this number.

## It is a measurement and never a move

Writing the record does not change any cut. `curation.floors` is the only owner
of a height that acts, and moving one there is a decision somebody takes after
reading this. What the command gives them is a number, its bootstrap interval,
the population it came off and a hash of every input.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.paths import tracked_name

#: The schema the record carries.
SCHEMA = 1

#: The label tier at and above which a picture is a keeper. The same three the
#: heads' `P(≥3)` cutpoint is about, so the curve is `P(the human agreed)`.
KEEPER_TIER = 3

#: The fitted agreement the crossing is read at. A half: below it the head is
#: wrong about this material more often than it is right.
CROSSING = 0.5

#: How many places the crossing is rounded to, and the grid a declared floor sits
#: on. Both reported, neither preferred silently — but as of 2026-08-22 both
#: standing heights in `curation.floors` read the grid, by Matt's ruling that two
#: floors on two grids cannot be compared. The three-place rounding stays in the
#: record because it is what the crossing rounds to and a reader should be able
#: to see the difference the grid makes.
PLACES = 3
FLOOR_GRID = 0.005

#: Resamples in the cluster bootstrap, and its seed. Clustered **on the place**
#: rather than on the picture: one location appears in the corpus many times at
#: many recipes, and treating those as independent draws would report an interval
#: several times too narrow.
BOOTSTRAP = 1000
BOOTSTRAP_SEED = 0


class FloorFitError(RuntimeError):
    """The fit cannot be run, or cannot be believed."""


# --------------------------------------------------------------------------- #
# The fit itself: stdlib only, so it is testable without a head or a GPU.
# --------------------------------------------------------------------------- #
def isotonic(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """`[(score, fitted agreement)]`, non-decreasing, by pool-adjacent-violators.

    `points` is `(score, outcome)` per picture, outcome in `{0.0, 1.0}`. Ties in
    the score are pooled before the pass — two pictures the head scored
    identically cannot be ordered by anything here, and leaving them adjacent and
    unpooled would let their input order decide which one the block starts at.

    Returns one `(score, value)` per distinct score, in ascending score order.
    """
    if not points:
        raise FloorFitError("an isotonic fit over no points has no crossing.")
    pooled: dict[float, list[float]] = {}
    for score, outcome in points:
        pooled.setdefault(float(score), []).append(float(outcome))
    # Blocks of (weight, sum), merged while the running means decrease.
    blocks: list[tuple[float, float, float]] = []  # (last score, weight, total)
    for score in sorted(pooled):
        outcomes = pooled[score]
        blocks.append((score, float(len(outcomes)), float(sum(outcomes))))
        while len(blocks) > 1:
            (_, weight_a, total_a), (score_b, weight_b, total_b) = blocks[-2], blocks[-1]
            if total_a / weight_a <= total_b / weight_b:
                break
            blocks[-2:] = [(score_b, weight_a + weight_b, total_a + total_b)]
    out: list[tuple[float, float]] = []
    at = 0
    for score in sorted(pooled):
        while blocks[at][0] < score:
            at += 1
        _, weight, total = blocks[at]
        out.append((score, total / weight))
    return out


def crossing(curve: list[tuple[float, float]], at: float = CROSSING) -> float | None:
    """The lowest score whose fitted agreement reaches `at`. `None` if none does.

    The **lowest**, not the nearest: the curve is non-decreasing, so every score
    above the first one that reaches a half also reaches it, and a floor is the
    bottom of the passing region rather than a point inside it.
    """
    for score, value in curve:
        if value >= at:
            return float(score)
    return None


def round_up(value: float, places: int = PLACES) -> float:
    """`value` rounded **up** at `places` decimals. A floor rounded down is not one."""
    scale = 10**places
    stepped = int(value * scale)
    if stepped / scale < value:
        stepped += 1
    return stepped / scale


def round_up_to_grid(value: float, grid: float = FLOOR_GRID) -> float:
    """`value` rounded up to the next multiple of `grid`, to three places."""
    steps = int(value / grid)
    if steps * grid < value:
        steps += 1
    return round(steps * grid, PLACES)


def bootstrap(
    points: list[tuple[float, float, str]],
    resamples: int = BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """A 95% interval on the crossing, resampling **places** rather than pictures.

    `points` is `(score, outcome, place)`. One location appears in these corpora
    many times, at many recipes, and its pictures are not independent draws —
    bootstrapping over rows would report an interval several times too narrow and
    make a bar look far better pinned than it is.
    """
    by_place: dict[str, list[tuple[float, float]]] = {}
    for score, outcome, place in points:
        by_place.setdefault(place, []).append((score, outcome))
    places = sorted(by_place)
    draws = random.Random(seed)
    found: list[float] = []
    for _ in range(max(0, int(resamples))):
        sample: list[tuple[float, float]] = []
        for _ in places:
            sample.extend(by_place[places[draws.randrange(len(places))]])
        where = crossing(isotonic(sample))
        if where is not None:
            found.append(where)
    found.sort()
    if not found:
        return {"resamples": 0, "low": None, "high": None, "no_crossing": resamples}
    return {
        "resamples": len(found),
        "low": round(found[int(0.025 * (len(found) - 1))], 4),
        "high": round(found[int(0.975 * (len(found) - 1))], 4),
        "no_crossing": max(0, int(resamples)) - len(found),
    }


# --------------------------------------------------------------------------- #
# Reading the head over its own corpus.
# --------------------------------------------------------------------------- #
def record_path(kind: str) -> Path:
    """Where one kind's fitted floor is written, beside the head that produced it.

    **Keyed by the kind, filed under the head.** The corpus is a kind's — one
    store, one population of pictures — and the scale is the judge's, because a
    floor is a point on the probabilities a particular artifact emits. Since the
    two per-kind judges became one, those are no longer the same name, so the file
    says both: `models/render/release_floor_<kind>.json`.
    """
    from fractal_wallpapers.models import render_train

    return render_train.head_dir() / f"release_floor_{finished.head_of(kind)}.json"


def digest_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def place_of(row: dict) -> str:
    """A stable name for the location a labeled picture is of.

    The corpus is many recipes over relatively few places, and the bootstrap has
    to resample the places. The family and the viewport are the identity; the
    mode, the curve and the map are the recipe.
    """
    return json.dumps([row.get("family"), row.get("viewport")], sort_keys=True, ensure_ascii=False)


def read(head: str, device: str = "auto", log=print) -> dict:
    """Every labeled picture of one head's corpus, through the **shipped** artifact.

    The shipped artifact and not a training checkpoint, because the number this
    produces is a curation cut and curation reads the shipped one. That is also
    what makes the head sha on the record the sha a `Restatement` can carry.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.models import renders, ship, train

    head = finished.head_of(head)
    resolution = finished.resolved(head)
    rows = resolution.scored()
    if not rows:
        raise FloorFitError(f"the {head} store holds no scored row to fit against.")

    names = [renders.job_name({**row, "_head": head}) for row in rows]
    crops = renders.crop_dir(head)
    pictures = [crops / f"{name}.jpg" for name in names]
    absent = [name for name, path in zip(names, pictures, strict=True) if not path.is_file()]
    if absent:
        raise FloorFitError(
            f"{len(absent)} of this head's {len(rows)} labeled pictures are not in the render "
            f"cache (e.g. {absent[:3]}). Run `fractal-wallpapers renders plan --head {head}` "
            f"and `renders build --head {head}` first — the fit reads the pictures this "
            f"repository makes, not the ones the corpus was labeled on somewhere else."
        )

    # The corpus is the kind's; the SCALE is the shipped judge's. One judge
    # answers for both kinds now, so these two names differ and the fit has to
    # keep them apart — a floor measured against the wrong artifact is a number
    # on a scale nothing emits.
    from fractal_wallpapers.models import render_train

    stamp = floors.live_stamp(floors.SCORING_HEAD)
    log(f"scoring {len(pictures)} labeled {head} pictures through {stamp[:12]}")
    model, config, where = render_train.load_checkpoint(
        ship.shipped_path(floors.SCORING_HEAD), device
    )
    classes = int(config["classes"])
    from fractal_wallpapers.models import scoring

    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 64}
    )
    read_rows = []
    for row, name, probability in zip(rows, names, probabilities, strict=True):
        cell = {
            "name": name,
            "batch": row["batch"],
            "label": int(row["score"]),
            "place": place_of(row),
        }
        for index in range(classes - 1):
            cell[f"p_ge{index + 2}"] = float(probability[index])
        read_rows.append(cell)
    return {
        "kind": head,
        "head": floors.SCORING_HEAD,
        "head_sha256": stamp,
        "classes": classes,
        "where": where,
        "rows": read_rows,
        "store": resolution.summary(),
    }


def fit(reading: dict, at: float = CROSSING, resamples: int = BOOTSTRAP) -> dict:
    """The whole measurement, as the record it becomes.

    Returns rather than writes. The value here is a *reading*, and putting it into
    `curation.floors` is a decision somebody takes after looking at it.
    """
    head, kind, stamp = reading["head"], reading["kind"], reading["head_sha256"]
    rows = reading["rows"]
    points = [(row["p_ge3"], float(row["label"] >= KEEPER_TIER), row["place"]) for row in rows]
    curve = isotonic([(score, outcome) for score, outcome, _ in points])
    where = crossing(curve, at)
    if where is None:
        raise FloorFitError(
            f"the {head} head's fitted agreement on the {kind} corpus never reaches {at:g} "
            f"anywhere on its scale, "
            f"so this corpus places no floor. The highest fitted value is {curve[-1][1]:.4f}."
        )
    keepers = sum(1 for _, outcome, _ in points if outcome)
    return {
        "schema": SCHEMA,
        "head": head,
        "kind": kind,
        "head_sha256": stamp,
        "value": round_up(where, PLACES),
        "crossing": round(where, 6),
        # Both roundings, because the number this is compared against was rounded
        # on the coarser grid and a comparison across two grids says nothing.
        "rounded_up_3_places": round_up(where, PLACES),
        "rounded_up_to_0_005": round_up_to_grid(where, FLOOR_GRID),
        "at": at,
        "keeper_tier": KEEPER_TIER,
        "interval_95": bootstrap(points, resamples),
        "population": {
            "pictures": len(rows),
            "places": len({row["place"] for row in rows}),
            "store_rows": reading["store"]["rows"],
            "superseded": reading["store"]["superseded"],
            "keepers": keepers,
            "keeper_share": round(keepers / len(rows), 4),
            "below_the_floor": sum(1 for row in rows if row["p_ge3"] < round_up(where, PLACES)),
        },
        # The two inputs, hashed. A floor is only as re-derivable as these are.
        "inputs": {
            "labels_sha256": digest_of(
                "\n".join(f"{row['name']}\t{row['label']}" for row in sorted(rows, key=key_of))
            ),
            "scores_sha256": digest_of(
                "\n".join(f"{row['name']}\t{row['p_ge3']!r}" for row in sorted(rows, key=key_of))
            ),
            "classes": reading["classes"],
        },
        "method": (
            f"the labels-derived crossover. Isotonic regression (pool-adjacent-violators, ties "
            f"pooled, non-decreasing) of P(the human said >={KEEPER_TIER}) against this head's "
            f"own P(>=3), over all {len(rows)} labeled {kind} pictures scored through the "
            f"shipped {head} artifact; the crossing is the LOWEST score whose fitted agreement "
            f"reaches "
            f"{at:g}, and the floor is that crossing rounded UP. Rounded up because a floor "
            f"rounded down admits material the fit did not vouch for."
        ),
        "reference_pool": (
            f"all {len(rows)} labeled {kind} pictures, over "
            f"{len({row['place'] for row in rows})} places, read through the shipped {head}"
        ),
    }


def key_of(row: dict) -> str:
    return str(row["name"])


def write(record: dict) -> Path:
    """Write the record as tracked text, LF, beside the head's other metadata."""
    path = record_path(record["kind"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def run(head: str, device: str = "auto", resamples: int = BOOTSTRAP, log=print) -> dict:
    """Read the corpus, fit the curve, write the record. Returns the record."""
    record = fit(read(head, device, log), resamples=resamples)
    record["wrote"] = tracked_name(write(record))
    return record


__all__ = [
    "BOOTSTRAP",
    "CROSSING",
    "KEEPER_TIER",
    "FLOOR_GRID",
    "PLACES",
    "SCHEMA",
    "FloorFitError",
    "bootstrap",
    "crossing",
    "digest_of",
    "fit",
    "isotonic",
    "place_of",
    "read",
    "record_path",
    "round_up",
    "round_up_to_grid",
    "run",
    "write",
]
