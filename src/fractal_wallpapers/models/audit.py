"""Auditing a training run: what its own record can prove, and what cannot be faked.

A long band is run overnight, killed, relaunched, and occasionally launched
twice. Afterwards there is a `metrics.json` and a checkpoint, and the question is
whether they are the same trajectory. Two instruments answer it, they answer
different halves of it, and confusing them is how a sound-looking check reads a
resume as a second writer.

## The arithmetic, and the one thing it can actually prove

[`serial_time`] reads `wall_seconds` against the sum of `history[*].seconds`. The
reading it used to be given — *"`wall_seconds` must be at least the sum, and when
it is far less a second process wrote that record"* — is **wrong for a resumed
run**, and the trainers here resume. The wall clock starts *after* the snapshot
is loaded, while `history` is restored *from* the snapshot: a run killed at epoch
nine and relaunched writes forty epochs of history and a wall that only ever
covered thirty-one of them. Nothing overlapped; the record is honest; the
inequality is simply not what it measures.

So what the arithmetic proves is narrower, and it is stated here as such. The
wall covers the **segment that wrote the record** — a contiguous suffix of the
history. Epochs before that suffix belong to an earlier segment, and from the
arithmetic alone a resume and a concurrent writer are indistinguishable. The one
thing it *can* prove is [`OVERLAPPED`]: when not even the final epoch fits inside
the wall, two epochs ran at once, and no resume explains that.

## Which is why a record now says where its segments are

A record carrying `segments` — one entry per launch, each naming the epochs it
ran and the wall it took — is checked exactly: every segment's wall must cover
its own epochs, and the segments must tile the history. That is the strict check
the prose always wanted, and it is available from the first run written after
this module existed. Records written before it have no `segments` and are read
the weaker way, which is the honest reading of what they hold.

## The instrument that does settle it

[`reproduce`] re-scores the run's own **selection slice** through its checkpoint
and compares against what the record says its best epoch scored. It needs neither
the log nor the wall clock: a snapshot is read once at startup and replaced
atomically, so two trajectories cannot mix mid-run, and agreement to
[`TOLERANCE`] proves the checkpoint and the record are one trajectory whoever
wrote them. The population is rebuilt from the tile corpus by the same seeded
draw the trainer used, and a slice that no longer reproduces is refused rather
than compared — a different population would make the disagreement mean nothing.

The result goes beside the run in `audit.json`, because the procedure had no
record slot at all: it lived in a commit message, which is not somewhere a reader
of a run directory will ever look.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import tracked_name

#: The schema every audit record carries.
SCHEMA = 1

#: How far apart a re-score and the record it reproduces may read. A forward pass
#: of the same weights over the same pictures in the same order is the same
#: arithmetic; what is left is float64 summation order inside the statistics.
TOLERANCE = 1e-8

#: The wall covers every epoch in the history. One segment, nothing overlapped.
SERIAL = "serial"

#: The wall covers a trailing segment only. The run was relaunched — or a second
#: process wrote the record. The arithmetic cannot tell those apart; a re-score
#: can.
RESUMED = "resumed"

#: Not even the final epoch fits inside the wall. Two epochs ran at once, and no
#: resume explains that. This is the only concurrency the arithmetic can prove.
OVERLAPPED = "overlapped"

#: The record carries no `wall_seconds` at all, so there is nothing to read.
UNRECORDED = "unrecorded"


def rounding_slack(epochs: int) -> float:
    """How far a sum of rounded tenths may sit from a rounded wall and mean nothing.

    Every second in a record is rounded to a tenth on the way in, so `n` epoch
    times summed against one more rounded number carry `(n + 1)` half-tenths of
    slop that is arithmetic rather than evidence.
    """
    return 0.05 * (epochs + 1)


def audit_path(name: str = "location", run: str | None = None) -> Path:
    """Where a run's audit is kept, beside the record it audits."""
    from fractal_wallpapers.models import train

    return train.head_dir(name, run) / "audit.json"


def serial_time(record: dict) -> dict:
    """Read a run record's clock against its own epochs.

    Returns the reading, the epochs the wall covers, and a sentence saying what
    that does and does not establish. Never raises: a record that reads
    [`OVERLAPPED`] is a finding, not a crash.
    """
    history = record.get("history") or []
    seconds = [float(row.get("seconds") or 0.0) for row in history]
    epochs = [row.get("epoch") for row in history]
    total = round(sum(seconds), 1)
    wall = record.get("wall_seconds")
    reading = {
        "wall_seconds": wall,
        "epoch_seconds": total,
        "epochs": len(history),
        "segments_recorded": bool(record.get("segments")),
    }

    if wall is None:
        return {
            **reading,
            "reading": UNRECORDED,
            "covers": None,
            "uncovered_epochs": len(history),
            "says": (
                "the record carries no wall clock, so the arithmetic says nothing about it "
                "at all. Only a re-score can speak for this run"
            ),
        }

    if record.get("segments"):
        return {**reading, **_by_segment(record, seconds, epochs)}

    slack = rounding_slack(len(history))
    if float(wall) + slack >= total:
        return {
            **reading,
            "reading": SERIAL,
            "covers": [epochs[0], epochs[-1]] if epochs else None,
            "uncovered_epochs": 0,
            "says": (
                "the wall covers every epoch in the history, so one segment wrote this "
                "record and nothing in it overlapped"
            ),
        }

    # The wall covers a suffix of the history. Take the longest suffix that fits:
    # the earliest epoch the segment that wrote this record could have begun at.
    running, first = 0.0, len(seconds)
    for index in range(len(seconds) - 1, -1, -1):
        if running + seconds[index] > float(wall) + slack:
            break
        running += seconds[index]
        first = index
    if first >= len(seconds):
        return {
            **reading,
            "reading": OVERLAPPED,
            "covers": None,
            "uncovered_epochs": len(history),
            "says": (
                f"the wall of {wall}s does not cover even the final epoch's {seconds[-1]}s, "
                "so two epochs ran at once. No resume explains that: a second process wrote "
                "this record"
            ),
        }
    return {
        **reading,
        "reading": RESUMED,
        "covers": [epochs[first], epochs[-1]],
        "uncovered_epochs": first,
        "says": (
            f"the wall of {wall}s covers epochs {epochs[first]}-{epochs[-1]} and no more, so "
            f"the {first} epoch(s) before them were run by an earlier segment. The clock "
            "starts after the snapshot loads and the history is restored from it, so a "
            "relaunch reads exactly like this — and so would a second writer. The "
            "arithmetic cannot separate them; a re-score can"
        ),
    }


def _by_segment(record: dict, seconds: list[float], epochs: list) -> dict:
    """The strict reading, for a record that says where its launches were."""
    by_epoch = dict(zip(epochs, seconds, strict=True))
    faults, covered = [], 0
    for segment in record["segments"]:
        first, last = segment["from_epoch"], segment["through_epoch"]
        own = [by_epoch[epoch] for epoch in epochs if first <= epoch <= last]
        covered += len(own)
        if float(segment["wall_seconds"]) + rounding_slack(len(own)) < round(sum(own), 1):
            faults.append(
                f"epochs {first}-{last} took {round(sum(own), 1)}s inside a segment whose "
                f"wall was {segment['wall_seconds']}s"
            )
    if covered != len(epochs):
        faults.append(f"the segments cover {covered} of {len(epochs)} epochs")
    if faults:
        return {
            "reading": OVERLAPPED,
            "covers": None,
            "uncovered_epochs": len(epochs) - covered,
            "says": "; ".join(faults) + " — two epochs ran at once inside one launch",
        }
    return {
        "reading": SERIAL,
        "covers": [epochs[0], epochs[-1]] if epochs else None,
        "uncovered_epochs": 0,
        "says": (
            f"{len(record['segments'])} launch(es), each one's wall covering its own epochs "
            "and the segments tiling the history: nothing in this record overlapped"
        ),
    }


def reproduce(
    name: str = "location",
    run: str | None = None,
    which: str = "best",
    device: str = "auto",
    log=None,
) -> dict:
    """Re-score a run's selection slice through its checkpoint and compare.

    The comparison is against the history row of the record's *own* best epoch,
    which is what the checkpoint claims to be. Every statistic that row carries
    at every regime the run drew is reproduced, because agreement on one number
    is a coincidence a dozen numbers is not.
    """
    import numpy

    from fractal_wallpapers.models import dataset, head, metrics, scoring, train
    from fractal_wallpapers.models import tiles as tile_module

    log = log or train.say
    if name != "location":
        raise ValueError(
            f"the selection-slice re-score is written for the location head, not {name!r}. "
            "That head chooses its epoch on a seeded slice this rebuilds from the corpus; "
            "the finished-render heads choose on a different statistic over a different "
            "population, and reproducing those means writing that reader too."
        )

    record = json.loads(train.metrics_path(name, run).read_text(encoding="utf-8"))
    config = json.loads(train.config_path(name, run).read_text(encoding="utf-8"))
    tags = list(config.get("regimes") or [tile_module.CANONICAL_REGIME.spelled])
    drawn = tuple(tile_module.regime_of(tag) for tag in tags)

    log(f"rebuilding the population at {tags}")
    locations, slice_record = train.population(name, drawn)
    said = record.get("selection_slice") or {}
    moved = {
        key: (said.get(key), slice_record.get(key))
        for key in ("seed", "train_locations", "groups", "selection_groups", "selection_locations")
        if said.get(key) != slice_record.get(key)
    }
    if moved:
        raise ValueError(
            f"the selection slice no longer reproduces: {moved}. The corpus has moved since "
            "this run, so a disagreement here would be the population's rather than the "
            "checkpoint's. Nothing is compared."
        )
    choosing = dataset.sides(locations)[dataset.SELECTION]
    labels = numpy.array([location.score for location in choosing])
    classes = int(config["classes"])

    checkpoint = train.checkpoint_path(name, which, run)
    model, saved_config, where = scoring.load(checkpoint, device)
    transform = scoring.transform_of(saved_config)
    recipe = {"batch_size": int(config["batch_size"])}

    best_epoch = record["best_epoch"]
    said_row = next((row for row in record["history"] if row["epoch"] == best_epoch), None)
    if said_row is None:
        raise ValueError(f"the record's best epoch {best_epoch} has no row in its own history")

    log(f"re-scoring {len(choosing)} selection locations through {checkpoint.name} on {where}")
    read: dict[str, float | None] = {}
    for index, regime in enumerate(drawn):
        probabilities = train.score(
            model,
            [location.canonical(regime.tag) for location in choosing],
            transform,
            where,
            classes,
            recipe,
        )
        entropy = metrics.cutpoint_cross_entropy(labels, probabilities, classes)
        read[f"selection_cutpoint_cross_entropy{regime.tag}"] = entropy
        if index == 0:
            read["selection_ap_ge2"] = metrics.average_precision(
                (labels >= 2).astype(int), probabilities[:, 0]
            )
            for cut in range(classes - 1):
                read[f"selection_auc_{head.cutpoint_label(cut)}"] = metrics.auc(
                    (labels >= cut + 2).astype(int), probabilities[:, cut]
                )
        log(f"  {tags[index]}: xent {train.shown(entropy)}")

    compared, worst, unread = {}, 0.0, []
    for key, value in sorted(read.items()):
        recorded = said_row.get(key)
        if recorded is None or value is None:
            compared[key] = {"recorded": recorded, "re_scored": value, "delta": None}
            unread.append(key)
            continue
        delta = float(value) - float(recorded)
        worst = max(worst, abs(delta))
        compared[key] = {"recorded": recorded, "re_scored": value, "delta": delta}

    return {
        "checkpoint": tracked_name(checkpoint),
        "which": which,
        "device": where,
        "best_epoch": best_epoch,
        "selection_locations": len(choosing),
        "regimes": tags,
        "statistics": compared,
        "not_compared": unread,
        "largest_absolute_delta": worst,
        "tolerance": TOLERANCE,
        "agrees": bool(worst <= TOLERANCE) and not unread,
    }


def run(
    name: str = "location",
    run_name: str | None = None,
    which: str = "best",
    device: str = "auto",
    log=None,
) -> dict:
    """Both readings of one run, as the record that goes beside it."""
    from fractal_wallpapers.models import train

    log = log or train.say
    record = json.loads(train.metrics_path(name, run_name).read_text(encoding="utf-8"))
    clock = serial_time(record)
    log(f"clock: {clock['reading']} — {clock['says']}")
    reproduction = reproduce(name, run_name, which=which, device=device, log=log)
    log(
        f"re-score: {'agrees' if reproduction['agrees'] else 'DISAGREES'} — largest delta "
        f"{reproduction['largest_absolute_delta']:.3e} against {TOLERANCE:.0e}"
    )
    return {
        "schema": SCHEMA,
        "head": name,
        "run": run_name,
        "record": tracked_name(train.metrics_path(name, run_name)),
        "clock": clock,
        "reproduction": reproduction,
        "verdict": "REPRODUCED" if reproduction["agrees"] else "DISAGREES",
    }


__all__ = [
    "OVERLAPPED",
    "RESUMED",
    "SCHEMA",
    "SERIAL",
    "TOLERANCE",
    "UNRECORDED",
    "audit_path",
    "reproduce",
    "rounding_slack",
    "run",
    "serial_time",
]
