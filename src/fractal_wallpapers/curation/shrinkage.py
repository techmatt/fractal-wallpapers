"""Re-read a candidate set's winner at label geometry, and price the winner's curse.

A location is called PRIMED when the best of its `k` candidates clears a bar.
That best is a **maximum over k noisy readings**, so it captures noise as well as
quality, and it does so more the wider the set gets. The calibration sheet
measured the noise directly: across a single doubling of geometry `P(>=4)` moves
by mean **-0.009** with sd **0.087**, and 46% of rows land in a different
0.10-wide band than the one they were drawn into. Unbiased, and imprecise.

Feed an unbiased-but-imprecise score into a maximum and the result is biased
upward — about two standard deviations' worth by `k = 40`, if the readings were
independent draws around one true value. A depth curve read off that maximum
therefore looks better than it is, **most of all at the large `k` the strategy
rests on**, which is the one place a wrong number would be expensive.

## What this measures, and how

For a sample of locations, take the candidate that was the running best of the
first `k` — at each of a few checkpoints — and **re-render it at label geometry
(1280x720 ss2) through its own recipe**, then score it on the same shipped
artifact. Nothing else moves: same mode, same map, same autolevel band, same
judge. The drop is the shrinkage, measured rather than modelled.

Two curves come out of that and **both are reported**. The **raw** curve is the
cumulative prime rate on the 640x360 readings, which is what every prime count
this project has quoted so far is. The **calibrated** curve is the same
locations counted on the re-read. The gap between them is the selection bias,
and quoting one for the other is the mistake this module exists to stop.

## What it does not do

It does not correct anything. The label-geometry read is another single noisy
reading of the same picture, not a truth: what it removes is the *selection*, by
drawing the noise again after the winner was chosen. The same argument applies
to the seated floor — the solve picks on a 640x360 score and reports that score
as the seated quality — and the fix there belongs to the solver.
"""

from __future__ import annotations

import collections
import json
import random
import statistics
import time
from pathlib import Path

from fractal_wallpapers.curation import hunt
from fractal_wallpapers.labeling.sheets import LABEL_RESOLUTION, LABEL_SUPERSAMPLE
from fractal_wallpapers.paths import tracked_name, under

#: The schema every row and record this module writes carries.
SCHEMA = 1

#: The subtree one shrinkage read lands in, under the regenerable tree.
UNIT = "shrinkage"

# `LABEL_RESOLUTION` and `LABEL_SUPERSAMPLE` — the geometry a person's label is
# taken at, and therefore the second reading. A candidate is 640x360 ss2; a
# finished sheet serves this. One doubling, which is the contrast the calibration
# sheet measured over.
#
# Imported at the top rather than spelled again: `labeling.sheets` owns them,
# because the sheet rule is what they are about. Two spellings of one geometry is
# a silent null — the day the sheet moves, a re-read holding its own copy goes on
# measuring the doubling it used to be, and nothing goes red. Both names stay in
# `__all__`, so what this module has always answered to still answers.

#: The widths the curve is re-read at. Not every `k`: the re-render is four times
#: a candidate's pixels and the answer wanted is the *shape* of the drop against
#: width, which five points carry. `1` is the no-selection control — a maximum
#: over one reading is not a maximum — and it is what the others are read
#: against.
CHECKPOINTS = (1, 5, 10, 20, 40)

#: How many locations each draw contributes. A correction term, not a second
#: experiment: enough that a mean drop has a standard error worth quoting, and
#: small enough that the whole read is minutes.
PER_ARM = 20

#: How many render workers the re-read spreads over. The judge stays in the
#: parent — one load of it, one batch at the end.
#:
#: **Three**, which is the locked render-pool shape rather than a tuning knob:
#: more than three `fractal-engine` processes at once makes this machine's
#: desktop unusable while the leg runs, and this leg drives the engine like any
#: other. It was six, which was the one leg here disagreeing with the rule.
WORKERS = 3


class ShrinkageRefused(RuntimeError):
    """A shrinkage read cannot be taken off what this run left behind."""


def shrinkage_dir(name: str) -> Path:
    """One read's own subtree: its pictures, its pairs, its record."""
    return under("curation", UNIT, str(name))


def pairs_path(name: str) -> Path:
    """One row a re-read candidate: both readings of it, side by side."""
    return shrinkage_dir(name) / "pairs.jsonl"


def record_path(name: str) -> Path:
    """What the read reports: the two curves, and the drop against width."""
    return shrinkage_dir(name) / "shrinkage.json"


def pictures_dir(name: str) -> Path:
    """Where the label-geometry re-renders land."""
    return shrinkage_dir(name) / "pictures"


# --------------------------------------------------------------------------- #
# Choosing what to re-read.
# --------------------------------------------------------------------------- #
def running_winners(rows: list, checkpoints=CHECKPOINTS) -> list:
    """The candidate that was the best of the first `k`, at each checkpoint.

    One location's own sequence, in the order it was made. The same candidate is
    usually the winner at several checkpoints — a set whose best landed at `k=3`
    wins at 5, 10, 20 and 40 — so the returned rows are **deduplicated** and each
    carries every checkpoint it won at. That is most of the saving: forty
    locations at five checkpoints is not two hundred renders.
    """
    ordered = sorted(rows, key=lambda row: int(row["k"]))
    out: dict = {}
    for k in checkpoints:
        held = [row for row in ordered if int(row["k"]) <= int(k)]
        if not held:
            continue
        best = max(held, key=lambda row: (float(row["p_ge4"]), -int(row["k"])))
        out.setdefault(str(best["key"]), {"row": best, "won_at": []})["won_at"].append(int(k))
    return [{**held["row"], "won_at": held["won_at"]} for held in out.values()]


def sample(sequence: list, per_arm: int = PER_ARM, seed: int = 0, checkpoints=CHECKPOINTS) -> list:
    """Locations spread over the arms and, inside an arm, over the rank bands.

    Stratified on the band rather than drawn flat, because the drop is being read
    against `k` and a sample that happened to sit in one band would carry that
    band's quality into the answer. A location that never reached the widest
    checkpoint is still eligible — its curve is read at the checkpoints it did
    reach and it is absent from the ones it did not, which is the same rule
    [`curation.depth.curves`] counts a location under.
    """
    by_location: dict = {}
    for row in sequence:
        by_location.setdefault(str(row["location"]), []).append(row)
    picked: list = []
    for arm in sorted({str(row["arm"]) for row in sequence}):
        cells: dict = {}
        for key, rows in by_location.items():
            if str(rows[0]["arm"]) != arm:
                continue
            cells.setdefault(str(rows[0].get("band")), []).append(key)
        order = sorted(cells)
        if not order:
            continue
        drawn: list = []
        pools = {
            band: random.Random(hunt.seed_of(seed, arm, band)).sample(keys, len(keys))
            for band, keys in cells.items()
        }
        at = dict.fromkeys(order, 0)
        while len(drawn) < int(per_arm):
            took = False
            for band in order:
                if len(drawn) >= int(per_arm):
                    break
                if at[band] < len(pools[band]):
                    drawn.append(pools[band][at[band]])
                    at[band] += 1
                    took = True
            if not took:
                break
        for key in drawn:
            for winner in running_winners(by_location[key], checkpoints):
                picked.append(winner)
    return picked


# --------------------------------------------------------------------------- #
# The second reading.
# --------------------------------------------------------------------------- #
def _render_one(payload: tuple) -> dict:
    """One candidate re-rendered at label geometry through its own recipe.

    A module-level function taking a tuple because it is what a process pool can
    carry: the workers hold no judge and no model, only the engine, and the
    scoring happens once in the parent over everything they made.
    """
    row, ledger_row, directory, resolution, supersample = payload
    from fractal_wallpapers.curation import colorize

    recipe = ledger_row.get("recipe") or {}
    place = ledger_row.get("location") or {}
    here = {
        "family": recipe.get("family") or place.get("family"),
        "viewport": recipe.get("viewport") or place.get("viewport"),
        "maxiter": int(recipe.get("maxiter") or place.get("maxiter") or 0),
    }
    geometry = {
        "resolution": list(resolution),
        "supersample": int(supersample),
        "maxiter": int(here["maxiter"]),
    }
    output = Path(directory) / f"{row['key']}.jpg"
    try:
        picture, stamp = colorize.render(
            here,
            str(row["mode"]),
            str(row["colormap"]),
            colorize.cyclic(),
            output,
            render_geometry=geometry,
            level=recipe.get("autolevel") is not None,
            band=colorize.band(),
        )
    except Exception as failure:  # noqa: BLE001 — a refused re-render is a recorded fact
        return {**row, "picture": None, "why": repr(failure)[:200]}
    return {
        **row,
        "picture": str(picture),
        "acted_at_label_geometry": bool((stamp or {}).get("acted")),
    }


def reread(
    name: str,
    picked: list,
    ledger: dict,
    workers: int = WORKERS,
    device: str = "auto",
    log=print,
) -> list:
    """Re-render every chosen candidate at label geometry and score the lot.

    The judge is loaded once in this process and run over the finished pictures,
    so the second reading differs from the first in the geometry and in nothing
    else — same artifact, same transform, same cutpoints.
    """
    from concurrent.futures import ProcessPoolExecutor

    from fractal_wallpapers.curation import colorize

    directory = pictures_dir(name)
    directory.mkdir(parents=True, exist_ok=True)
    payloads = []
    for row in picked:
        stored = ledger.get(str(row["key"]))
        if stored is None:
            log(f"[shrinkage] {row['key']} is not in the ledger and cannot be re-rendered")
            continue
        payloads.append(
            (row, stored, str(directory), list(LABEL_RESOLUTION), int(LABEL_SUPERSAMPLE))
        )
    started = time.perf_counter()
    log(f"[shrinkage] {len(payloads)} candidate(s) at label geometry over {workers} worker(s)")
    made: list = []
    if int(workers) <= 1:
        for at, payload in enumerate(payloads, start=1):
            made.append(_render_one(payload))
            if at % 25 == 0:
                log(f"[shrinkage] {at}/{len(payloads)} in {time.perf_counter() - started:.0f}s")
    else:
        with ProcessPoolExecutor(max_workers=int(workers)) as pool:
            for at, done in enumerate(pool.map(_render_one, payloads), start=1):
                made.append(done)
                if at % 25 == 0:
                    log(f"[shrinkage] {at}/{len(payloads)} in {time.perf_counter() - started:.0f}s")
    log(f"[shrinkage] rendered in {time.perf_counter() - started:.0f}s; scoring")
    judge = colorize.load_judge(device)
    out: list = []
    for row in made:
        if not row.get("picture"):
            out.append(row)
            continue
        verdict = colorize.score_picture(judge, Path(row["picture"]))
        out.append(
            {
                **row,
                "label_p_ge4": round(float(verdict.get("p_ge4") or 0.0), 6),
                "label_p_ge3": round(float(verdict.get("p_ge3") or 0.0), 6),
                "delta_p_ge4": round(float(verdict.get("p_ge4") or 0.0) - float(row["p_ge4"]), 6),
                "picture": tracked_name(Path(row["picture"])),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# The two curves.
# --------------------------------------------------------------------------- #
def curves(pairs: list, sequence: list, bars, checkpoints=CHECKPOINTS) -> dict:
    """Raw against calibrated, per arm and per checkpoint, at each bar.

    The raw rate counts a sampled location primed at `k` when the best of its
    first `k` **640x360** readings clears the bar. The calibrated rate counts the
    same location on the **label-geometry** reading of that same winner. Same
    locations, same winners, same bar: the only thing that moves between the two
    columns is which reading of the winning picture is believed.
    """
    label = {str(row["key"]): row for row in pairs if row.get("label_p_ge4") is not None}
    by_location: dict = {}
    for row in sequence:
        by_location.setdefault(str(row["location"]), []).append(row)
    sampled = {str(row["location"]) for row in pairs}
    out: dict = {}
    for arm in sorted({str(row["arm"]) for row in pairs}):
        places = sorted(
            key for key in sampled if str(by_location[key][0]["arm"]) == arm and key in by_location
        )
        block: dict = {"locations": len(places), "checkpoints": {}}
        for k in checkpoints:
            raw_hits: dict = {bar: 0 for bar in bars}
            cooked: dict = {bar: 0 for bar in bars}
            drops: list = []
            alive = 0
            for key in places:
                held = [row for row in by_location[key] if int(row["k"]) <= int(k)]
                if not held or len(by_location[key]) < min(int(k), 1):
                    continue
                if max(int(row["k"]) for row in by_location[key]) < int(k):
                    # The location never reached this width. Out of the
                    # denominator here rather than counted as a failure, which is
                    # the rule the raw curve is computed under too.
                    continue
                alive += 1
                best = max(held, key=lambda row: (float(row["p_ge4"]), -int(row["k"])))
                paired = label.get(str(best["key"]))
                for bar in bars:
                    raw_hits[bar] += int(float(best["p_ge4"]) >= bar)
                    if paired is not None:
                        cooked[bar] += int(float(paired["label_p_ge4"]) >= bar)
                if paired is not None:
                    drops.append(float(paired["label_p_ge4"]) - float(best["p_ge4"]))
            block["checkpoints"][str(k)] = {
                "locations": alive,
                "re_read": len(drops),
                "mean_drop": round(statistics.fmean(drops), 5) if drops else None,
                "median_drop": round(statistics.median(drops), 5) if drops else None,
                "sd_drop": round(statistics.pstdev(drops), 5) if len(drops) > 1 else None,
                "se_drop": (
                    round(statistics.pstdev(drops) / (len(drops) ** 0.5), 5)
                    if len(drops) > 1
                    else None
                ),
                **{
                    _tag(bar): {
                        "raw_primed": raw_hits[bar],
                        "raw_rate": round(raw_hits[bar] / max(1, alive), 5),
                        "calibrated_primed": cooked[bar],
                        "calibrated_rate": round(cooked[bar] / max(1, alive), 5),
                        "ratio": (round(cooked[bar] / raw_hits[bar], 4) if raw_hits[bar] else None),
                    }
                    for bar in bars
                },
            }
        out[arm] = block
    return out


def pooled(pairs: list, checkpoints=CHECKPOINTS) -> dict:
    """The drop against the width the winner was chosen over, pooled over arms.

    A candidate wins at several checkpoints, so it appears at several widths
    here. That is the intended reading — the question is what a winner *of a set
    this wide* loses on a second look — and it is why the row carries `won_at`
    rather than one width.
    """
    out: dict = {}
    for k in checkpoints:
        held = [
            row
            for row in pairs
            if row.get("label_p_ge4") is not None and int(k) in (row.get("won_at") or [])
        ]
        if not held:
            continue
        drops = [float(row["delta_p_ge4"]) for row in held]
        out[str(k)] = {
            "winners": len(held),
            "mean_drop": round(statistics.fmean(drops), 5),
            "sd": round(statistics.pstdev(drops), 5) if len(drops) > 1 else None,
            "se": (
                round(statistics.pstdev(drops) / (len(drops) ** 0.5), 5) if len(drops) > 1 else None
            ),
            "share_falling": round(sum(1 for value in drops if value < 0) / len(drops), 4),
            "levelling_matched": sum(
                1
                for row in held
                if bool(row.get("acted")) == bool(row.get("acted_at_label_geometry"))
            ),
        }
        matched = [
            float(row["delta_p_ge4"])
            for row in held
            if bool(row.get("acted")) == bool(row.get("acted_at_label_geometry"))
        ]
        if matched:
            out[str(k)]["mean_drop_matched_levelling"] = round(statistics.fmean(matched), 5)
    return out


def measure(
    name: str,
    sequence: list,
    ledger: dict,
    bars,
    per_arm: int = PER_ARM,
    seed: int = 0,
    workers: int = WORKERS,
    device: str = "auto",
    checkpoints=CHECKPOINTS,
    log=print,
) -> dict:
    """The whole read: draw, re-render, score, and write both curves down."""
    if not sequence:
        raise ShrinkageRefused(
            "the sequence holds no candidate, so there is no winner to re-read. A depth "
            "run writes its sequence as it goes; an empty file means none landed."
        )
    picked = sample(sequence, per_arm=per_arm, seed=seed, checkpoints=checkpoints)
    log(
        f"[shrinkage] {len({row['location'] for row in picked})} location(s), "
        f"{len(picked)} distinct winner(s) to re-read"
    )
    pairs = reread(name, picked, ledger, workers=workers, device=device, log=log)
    path = pairs_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in pairs:
            handle.write(json.dumps({"schema": SCHEMA, **row}, ensure_ascii=False) + "\n")
    record = {
        "schema": SCHEMA,
        "name": name,
        "label_geometry": {
            "resolution": list(LABEL_RESOLUTION),
            "supersample": LABEL_SUPERSAMPLE,
        },
        "checkpoints": list(checkpoints),
        "per_arm": int(per_arm),
        "sampled_locations": len({row["location"] for row in picked}),
        "re_rendered": sum(1 for row in pairs if row.get("label_p_ge4") is not None),
        "failed": sum(1 for row in pairs if row.get("label_p_ge4") is None),
        "drop_by_width": pooled(pairs, checkpoints),
        "curves": curves(pairs, sequence, bars, checkpoints),
        "by_mode": _by_mode(pairs),
        "pairs_path": tracked_name(path),
    }
    out = record_path(name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[shrinkage] {tracked_name(out)}")
    return record


def _by_mode(pairs: list) -> dict:
    """The drop by mode, because a re-level is more likely in some of them."""
    out: dict = {}
    held = collections.defaultdict(list)
    for row in pairs:
        if row.get("label_p_ge4") is not None:
            held[str(row["mode"])].append(float(row["delta_p_ge4"]))
    for mode, drops in sorted(held.items()):
        out[mode] = {
            "winners": len(drops),
            "mean_drop": round(statistics.fmean(drops), 5),
            "sd": round(statistics.pstdev(drops), 5) if len(drops) > 1 else None,
        }
    return out


def _tag(bar: float) -> str:
    return f"bar_{bar:.2f}".replace(".", "")


__all__ = [
    "CHECKPOINTS",
    "LABEL_RESOLUTION",
    "LABEL_SUPERSAMPLE",
    "PER_ARM",
    "SCHEMA",
    "UNIT",
    "WORKERS",
    "ShrinkageRefused",
    "curves",
    "measure",
    "pairs_path",
    "pictures_dir",
    "pooled",
    "record_path",
    "reread",
    "running_winners",
    "sample",
    "shrinkage_dir",
]
