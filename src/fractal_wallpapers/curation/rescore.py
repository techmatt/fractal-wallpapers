"""Reading every candidate the pool holds through today's finished-render heads.

A release row carries the scores the run that made it read, on the artifact that
was shipped that night. That is the right thing for a record to hold — it is what
the decision was actually taken on — and it is the wrong thing to *compare*
across runs, because two of this project's six runs were judged by a strange head
that has since been replaced. 125 rows sit on the retired three-class artifact:
they have no `P(≥4)` at all, and their `P(≥3)` is a point on a scale that no
longer exists.

So this pass reads every candidate picture again, through the head that is
shipped now, and writes what it finds into a **second** block on the row.

## The original scores are never touched

`scores` stays exactly as the run wrote it. It is that run's provenance, and a
pass that overwrote it would delete the only evidence of what the release path
decided on the night it decided. `scores_current` is the readable-today number,
it carries the sha of the artifact that produced it, and a reader that wants to
compare rows across runs reads that one.

## Each row is read by its own head, not by both

A candidate belongs to the judge whose slots paid for it: the smooth judge owns
the smooth coloring and the strange judge owns every other mode. Reading a
strange picture through the smooth head would produce a number, and the number
would be about material that head has never been trained on. The pool holds rows
of both kinds, so the pass loads both heads — and each row is scored by one.

## The picture is the candidate render, at candidate geometry

`pictures/NNNN.jpg`, 640x360, the render the gate decision was taken on. Not the
release PNG: only 153 rows have one, and a floor read at one geometry and applied
at another is two different measurements wearing one number.

## The pool is in two stores, and both are read and both are written back

A run's candidates are release rows in the tracked store. A **gallery pass's**
attempts are rows in [`curation.gallery_store`], under `artifacts/` with a
tracked manifest, and one pass makes more of them than every run has made in
total. A re-score that read only the tracked store would leave the larger half of
the pool carrying a retired head's numbers — and `gallery.pool_candidates` reads
`scores_current` where a row has one, so the next pass would rank a re-scored run
row against a stale pass row on two different scales. That is the failure this
project has already made once, and it is the reason this pass exists at all.

A row with **no score** is skipped rather than read: a failed render is a decision
with a reason and no number, and it has no picture to read either.
"""

from __future__ import annotations

from fractal_wallpapers.curation import records
from fractal_wallpapers.curation import run as run_module

#: The block a re-read writes. Named for what it is rather than for when it was
#: written: `scores` is the run's own reading and this is the live head's, and a
#: name like `scores_v2` would need a paragraph of history to place.
BLOCK = "scores_current"

#: Where a candidate's own render lives inside its run's directory.
PICTURES = "pictures"


class RescoreError(RuntimeError):
    """The pool cannot be read, or cannot be scored."""


def picture_of(row: dict):
    """The candidate render one release row was decided on.

    Off the run and the candidate id rather than off `row["picture"]`, which is
    the release PNG on a released row, the candidate JPEG on a passed-over one
    and `None` on a killed one. One geometry for every row or the readings are
    not comparable.

    **`source` wins where a row has one.** A gallery pass records its own decision
    about a candidate an earlier run made, under its own pass id and its own
    candidate id — two decisions about one picture — and the picture is still the
    earlier run's. Without this the pass's seats would resolve to a render nobody
    ever made, and this whole pass would refuse over rows that are perfectly
    readable. A row with no `source` is every row written before passes existed,
    and its candidate is its own.
    """
    source = row.get("source") or {}
    run = str(source.get("run") or row["run"])
    candidate = str(source.get("candidate") or row["candidate"])
    return run_module.run_dir(run) / PICTURES / f"{candidate}.jpg"


def scoring_artifact(run: str) -> dict:
    """Which artifact each head actually was on the night this run was made.

    Off the run's own summary and not off the row. A row carries
    `advisory.head_sha256` or `bar.head_sha256`, and on a gated head the second
    of those is the artifact the *bar* was measured against rather than the one
    that scored the row — `floors.release_cut` says so deliberately. Reading bar
    provenance as score provenance is how a scale shift goes unnoticed.
    """
    import json

    path = records.root() / "runs" / f"{run}.json"
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("config", {}).get("heads") or {})


def run(device: str = "auto", log=print) -> dict:
    """Read the whole pool through the live heads and write `scores_current`.

    Idempotent: a second pass over an unchanged pool through unchanged heads
    writes the same bytes.
    """
    from fractal_wallpapers.curation import floors, gallery_store
    from fractal_wallpapers.models import finished_scoring, scoring, ship, train

    rows = [
        row
        for row in [*records.read_decisions(records.RELEASE), *gallery_store.read()]
        if (row.get("scores") or {}).get("p_ge3") is not None
    ]
    if not rows:
        raise RescoreError("the pool holds no scored row, so there is nothing to read.")

    by_head: dict[str, list[dict]] = {}
    for row in rows:
        head = (row.get("scores") or {}).get("head")
        if not head:
            raise RescoreError(
                f"release row {row['key']!r} names no head, so nothing can say which judge "
                f"should read its picture."
            )
        by_head.setdefault(head, []).append(row)

    absent = [row["key"] for row in rows if not picture_of(row).is_file()]
    if absent:
        raise RescoreError(
            f"{len(absent)} of the pool's {len(rows)} candidate renders are not on disk "
            f"(e.g. {absent[:3]}). The pool's pictures live under the regenerable tree — "
            f"check `storage status` before deciding they are gone."
        )

    read: dict[str, dict] = {}
    per_head = {}
    for head in sorted(by_head):
        mine = by_head[head]
        stamp = floors.live_stamp(head)
        log(f"[rescore] {len(mine)} {head} candidate(s) through {stamp[:12]}")
        model, config, where = finished_scoring.load(ship.shipped_path(head), device)
        classes = int(config["classes"])
        probabilities = train.score(
            model,
            [picture_of(row) for row in mine],
            scoring.transform_of(config),
            where,
            classes,
            {"batch_size": 64},
        )
        for row, probability in zip(mine, probabilities, strict=True):
            block = {"head": head, "head_sha256": stamp}
            for index in range(classes - 1):
                block[f"p_ge{index + 2}"] = float(probability[index])
            block["rank_score"] = float(sum(probability))
            read[row["key"]] = block
        per_head[head] = {"rows": len(mine), "head_sha256": stamp, "classes": classes}

    shift = _shift(rows, read)
    wrote = _write(rows, read, log)
    return {
        "schema": records.SCHEMA,
        "block": BLOCK,
        "pool_rows": len(rows),
        "heads": per_head,
        "shift": shift,
        "wrote": wrote,
    }


def _shift(rows: list[dict], read: dict) -> dict:
    """What the re-read did to rows the live head had already scored.

    On a row whose run was judged by the artifact that is shipped now, this pass
    is the same head over the same picture and the answer should be the number
    already on the row. Reported rather than asserted, because "should be
    identity" is a claim about the whole scoring path — the transform, the
    batching, the half-precision artifact — and the cheapest way to find out that
    something in it moved is to look.
    """
    stamps: dict[str, dict] = {}
    same: list[float] = []
    moved: dict[str, dict] = {}
    for row in rows:
        head = row["scores"]["head"]
        stamps.setdefault(row["run"], scoring_artifact(row["run"]))
        was = str(stamps[row["run"]].get(head) or "")
        now = read[row["key"]]["head_sha256"]
        before, after = row["scores"].get("p_ge3"), read[row["key"]]["p_ge3"]
        if was and now.startswith(was) and before is not None:
            same.append(abs(float(after) - float(before)))
        else:
            cell = moved.setdefault(f"{head} {was or 'unrecorded'}", {"rows": 0, "gained_p_ge4": 0})
            cell["rows"] += 1
            cell["gained_p_ge4"] += int(
                row["scores"].get("p_ge4") is None and read[row["key"]].get("p_ge4") is not None
            )
    return {
        "already_current": {
            "rows": len(same),
            "identical": sum(1 for delta in same if delta == 0.0),
            "max_abs_delta": max(same) if same else None,
            "mean_abs_delta": (sum(same) / len(same)) if same else None,
        },
        "re_scaled": dict(sorted(moved.items())),
    }


def _write(rows: list[dict], read: dict, log) -> dict:
    """Put the block on every row and write it back to the store it came from.

    Through each store's own upsert, so the key order and the file layout stay the
    store's — and so a rejection block a person added survives, which `_carry`
    guarantees and a hand-rolled rewrite would not.

    **Routed by stage**, which is what says which store a row lives in: a release
    row is a decision about a slot and belongs to the tracked store, and a gate row
    is a pass's attempt and belongs to that pass's own. A pass whose store was
    rewritten has its manifest saved again in the same call, because a store the
    manifest no longer describes reads as `changed` to every later check.
    """
    from fractal_wallpapers.curation import gallery_store

    by_run: dict[tuple, list[dict]] = {}
    for row in rows:
        stage = str(row.get("stage") or records.RELEASE)
        by_run.setdefault((stage, row["run"]), []).append({**row, BLOCK: read[row["key"]]})
    out = {}
    for stage, name in sorted(by_run):
        mine = by_run[(stage, name)]
        if stage == records.GATE:
            _, total, new = gallery_store.write(name, mine)
            gallery_store.save(name, log=lambda line: log(f"[rescore] {line}"))
        else:
            _, total, new = records.write_decisions(records.RELEASE, name, mine)
        out[f"{name}/{stage}"] = total
        log(f"[rescore] {name} {stage}: {total} row(s) written, {new} new")
    return out


__all__ = ["BLOCK", "PICTURES", "RescoreError", "picture_of", "run", "scoring_artifact"]
