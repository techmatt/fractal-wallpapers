"""The end-to-end path: harvest supply in, released wallpapers out.

Five stages, each one a module of its own and each one writing what the next one
reads:

```text
intake     the union of every walk, ranked best-first per partition
budget     how many pictures to make, and for which judge
colorize   a palette candidate set, the head's pick, a render, a verdict
selection  top-N per judge under the slot, supply and look caps
release    the selected rows again at full resolution, workers rendering
```

This module holds the wiring and the arithmetic that belongs to no single stage —
which run this is, where its records go, what the funnel's counts were — and
nothing else. Every decision it appears to make is imported from the module that
owns it.

## Two things it insists on

**The release plan is re-solved after the colorize, not before.** The attempt
budget's slot projection is the best estimate available before a single picture
exists; the allocation the release actually spends is solved over the partitions
that ended up with a *scored candidate*, which is a different and smaller set
whenever a render failed or a partition's supply ran out mid-run.

**Nothing is padded, backfilled or redistributed.** A judge that cannot fill its
quota under the caps ships fewer. A slot a thin partition could not use is not
handed to a partition that had plenty — that is the thin-supply rule undone one
level up — and a short-fill is printed with the three numbers that make it
attributable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers.curation import (
    budget as budget_module,
)
from fractal_wallpapers.curation import (
    colorize,
    floors,
    intake,
    records,
    release,
    selection,
    sheet,
)
from fractal_wallpapers.paths import repo_root

#: The share of a release's slots the strange judge fills. Half, which is a
#: policy about what a release looks like and not a measurement — the two judges
#: cover disjoint sets of colorings and neither is the point of the project on
#: its own.
STRANGE_SHARE = 0.5

#: What a release picture is rendered at.
RELEASE_RESOLUTION = (2560, 1440)
RELEASE_SUPERSAMPLE = 4


def run_dir(run: str) -> Path:
    """Where a run's pictures and caches live. Ignored, and regenerable."""
    return repo_root() / "artifacts" / "curation" / "runs" / str(run)


def curate(
    run: str,
    n: int,
    seed: int = 0,
    strange_share: float = STRANGE_SHARE,
    attempts: int | None = None,
    workers: int = release.DEFAULT_WORKERS,
    ephemeral: bool = False,
    ledgers=None,
    device: str = "auto",
    skip_release: bool = False,
    log=print,
) -> dict:
    """One release, end to end. Returns the run's own summary record."""
    started = time.monotonic()
    if ephemeral:
        records.use(records.scratch_root(run))
        log(f"[records] ephemeral: {records.root()}")
        records.assert_isolated(run)
    else:
        records.use(None)
        log(f"[records] durable: {records.root()}")

    directory = run_dir(run)
    directory.mkdir(parents=True, exist_ok=True)

    # --- intake ---------------------------------------------------------- #
    offer, supply = intake.ranked(ledgers)
    for line in intake.supply_lines(supply):
        log(f"[intake] {line}")
    claims = intake.guaranteed(supply)
    caps = intake.emit_caps(offer)
    log(
        f"[intake] {supply['passing']} of {supply['found']} above the junk floor "
        f"({floors.JUNK_FLOOR}), {supply['good']} above the good floor ({floors.GOOD_FLOOR}); "
        f"{len(claims)} partition(s) owed a guaranteed slot"
    )
    by_key = {row["key"]: row for rows in offer.values() for row in rows}

    # --- budget ---------------------------------------------------------- #
    plan, budget_record = budget_module.plan(
        offer, n, strange_share, budget=attempts, guarantees=claims
    )
    for line in budget_module.fill_lines(budget_record, {}):
        log(f"[budget] {line}")

    # --- colorize -------------------------------------------------------- #
    candidate_log = directory / "candidates.jsonl"
    done = _resume(candidate_log)
    colorizer = colorize.Colorizer(directory, seed, device, log)
    picked = colorize.anchors(colorizer.pool, len(plan), seed)
    rows = list(done.values())
    for index, attempt in enumerate(plan):
        if index in done:
            continue
        row = colorize.annotate(
            colorizer.attempt(attempt, by_key[attempt.key], picked[index], index)
        )
        rows.append(row)
        with candidate_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        verdict = (
            f"P(>=3) {row['p_ge3']:.4f}"
            if row.get("p_ge3") is not None
            else f"FAILED {row.get('error')}"
        )
        log(
            f"[colorize] {index + 1}/{len(plan)} {attempt.head} {attempt.partition} "
            f"{row.get('mode')}/{row.get('colormap')} {verdict}"
        )
    rows.sort(key=lambda row: row["attempt"])
    scored = [row for row in rows if row.get("p_ge3") is not None]
    realized = budget_module.realized(scored)
    for line in budget_module.fill_lines(budget_record, realized):
        log(f"[budget] {line}")

    # --- selection ------------------------------------------------------- #
    selected, log_rows, split = _select(scored, n, strange_share, caps, claims, log)

    # --- release --------------------------------------------------------- #
    released, release_record = _release(selected, by_key, directory, workers, skip_release, log)

    # --- records --------------------------------------------------------- #
    summary = _record(
        run=run,
        rows=rows,
        scored=scored,
        selected=selected,
        released=released,
        log_rows=log_rows,
        split=split,
        supply=supply,
        budget_record=budget_record,
        release_record=release_record,
        realized=realized,
        directory=directory,
        ledgers=ledgers,
        n=n,
        seed=seed,
        strange_share=strange_share,
        seconds=time.monotonic() - started,
        log=log,
    )
    records.use(None)
    return summary


def _resume(path: Path) -> dict:
    """Attempts already made, by index. A killed run continues rather than restarts."""
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[int(row["attempt"])] = row
    return out


def _select(scored, n, strange_share, caps, claims, log):
    """Two disjoint judge passes, one look counter across both."""
    slots = budget_module.head_slots(n, strange_share)
    by_head = {head: [row for row in scored if row["head"] == head] for head in budget_module.HEADS}
    entries = {head: selection.entries(rows) for head, rows in by_head.items()}
    owed, unplaced = budget_module.assign_guarantees(
        [p for p in claims if any(e["partition"] == p for v in entries.values() for e in v)],
        slots,
    )

    used: dict = {}
    selected, log_rows, allocations = [], [], {}
    for head in budget_module.HEADS:
        present = {entry["partition"] for entry in entries[head]}
        mine = {p for p, h in owed.items() if h == head and p in present}
        allocation = intake.slots(present, slots[head], mine, caps=None)
        allocations[head] = allocation
        picks, rows = selection.select(
            entries[head],
            allocation,
            {p: caps.get(p, 0) for p in present},
            used,
            guarantees=mine,
        )
        for row in rows:
            row["head"] = head
        selected.extend(picks)
        log_rows.extend(rows)

    split = {
        "requested": n,
        "strange_share_target": strange_share,
        "head_slots": slots,
        "head_eligible": {head: len(v) for head, v in entries.items()},
        "head_selected": {
            head: sum(1 for entry in selected if entry["row"]["head"] == head)
            for head in budget_module.HEADS
        },
        "partition_slots": allocations,
        "emit_caps": dict(caps),
        "cluster_cap": floors.CLUSTER_CAP,
        "cluster_cap_skips": sum(1 for row in log_rows if row.get("skipped") == "cluster_cap"),
        "guarantee": {
            "owed": dict(sorted(owed.items())),
            "unplaced": list(unplaced),
            "slots_taken": sum(1 for row in log_rows if row.get("slot_source") == "guarantee"),
        },
        "short_by": max(0, n - len(selected)),
    }
    if split["short_by"]:
        log(
            f"[select] SHORT-FILL {len(selected)}/{n}: "
            + ", ".join(
                f"{head} {split['head_selected'][head]}/{slots[head]} "
                f"(eligible {split['head_eligible'][head]})"
                for head in budget_module.HEADS
            )
            + f". Shipping fewer rather than filling past a slot, supply or look cap "
            f"({split['cluster_cap_skips']} look-cap skips)."
        )
    log(
        f"[select] {len(selected)} selected: "
        + ", ".join(f"{head} {split['head_selected'][head]}" for head in budget_module.HEADS)
        + f"; {split['guarantee']['slots_taken']} guarantee slot(s)"
    )
    return selected, log_rows, split


def _release(selected, by_key, directory, workers, skip, log):
    """The full-resolution pass. The parent writes every record, in plan order."""
    where = directory / "release"
    where.mkdir(parents=True, exist_ok=True)
    stamps = where / "autolevel_stamps.jsonl"
    geometry = {
        "resolution": list(RELEASE_RESOLUTION),
        "supersample": RELEASE_SUPERSAMPLE,
    }

    tasks, done, reused = [], {}, []
    for entry in selected:
        row = entry["row"]
        identifier = entry["id"]
        picture = where / f"{identifier}.png"
        if skip or release.resumable(picture):
            # Reusing a picture is only reuse when there is one. `--skip-release`
            # over a run that has never rendered leaves the row unreleased, and
            # counting it as reused would report a release that did not happen.
            if picture.is_file():
                done[identifier] = picture
                reused.append(identifier)
            continue
        tasks.append(
            release.Task(
                id=identifier,
                row={
                    "family": row["family"],
                    "viewport": row["viewport"],
                    "maxiter": by_key[row["key"]].get("maxiter"),
                },
                colormap=row["colormap"],
                mode=row["mode"],
                output=str(picture),
                geometry={**geometry, "maxiter": int(by_key[row["key"]]["maxiter"])},
            )
        )

    def sink(task, result):
        """THE parent-side writer: everything durable about a release render, here."""
        if result.ok:
            done[task.id] = Path(result.info["picture"])
        else:
            log(f"[release] {task.id} failed at full resolution: {result.error}")
        if result.stamp is not None:
            with stamps.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps({"id": task.id, "autolevel": result.stamp}, ensure_ascii=False)
                    + "\n"
                )
        with (where / "timing.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    {
                        "id": task.id,
                        "seconds": round(result.seconds, 3),
                        "mode": task.mode,
                        "ok": result.ok,
                        **geometry,
                    }
                )
                + "\n"
            )

    record = release.run_pass(tasks, workers, sink, log)
    record["reused"] = len(reused)
    record["geometry"] = geometry
    # Plan order, not completion order: a concurrent pass finishes out of order
    # and everything downstream lays the pictures out in the order given here.
    return [(entry["id"], done[entry["id"]]) for entry in selected if entry["id"] in done], record


def _record(**k) -> dict:
    """Write every record the run leaves behind, and return its own summary."""
    run, rows, scored, selected = k["run"], k["rows"], k["scored"], k["selected"]
    directory = k["directory"]
    released = dict(k["released"])
    chosen = {entry["id"] for entry in selected}
    group_of = {entry["id"]: entry["group"] for entry in selection.entries(scored)}
    source = {row["id"]: row.get("slot_source") for row in k["log_rows"] if row.get("picked")}
    skipped = {row["id"] for row in k["log_rows"] if row.get("skipped") == "cluster_cap"}

    gate_rows = [
        records.decision(
            run=run,
            stage=records.GATE,
            candidate=f"{row['attempt']:04d}",
            verdict="kept" if row.get("p_ge3") is not None else "dropped",
            row=row,
            reason=row.get("error"),
            picture=row.get("picture"),
        )
        for row in rows
    ]
    # The full-resolution render is its OWN render: the operator measures and
    # stamps it at release geometry rather than inheriting the candidate's curve,
    # so a released row has two stamps and they are different facts. `autolevel`
    # stays the stamp of the render the *decision* was taken on; this is the one
    # for the picture that shipped.
    at_release = _release_stamps(directory)
    release_rows = []
    for row in scored:
        identifier = f"{row['attempt']:04d}"
        picture = released.get(identifier)
        decision = records.decision(
            run=run,
            stage=records.RELEASE,
            candidate=identifier,
            verdict="released" if identifier in chosen else "passed_over",
            row=row,
            reason="a third picture of a look already taken twice"
            if identifier in skipped
            else None,
            slot_source=source.get(identifier),
            group=group_of.get(identifier),
            picture=(str(Path(picture).relative_to(directory)) if picture else row.get("picture")),
        )
        decision["release_autolevel"] = at_release.get(identifier)
        release_rows.append(decision)

    counts = {
        "found": k["supply"]["found"],
        "above_junk_floor": k["supply"]["passing"],
        "above_good_floor": k["supply"]["good"],
        "unscored": k["supply"]["unscored"],
        "attempts_planned": k["budget_record"]["planned"],
        "attempts_made": len(rows),
        "attempts_scored": len(scored),
        "attempts_failed": len(rows) - len(scored),
        "selected": len(selected),
        "released": len(released),
        "requested": k["n"],
    }
    cuts = floors.summary()
    config = {
        "seed": k["seed"],
        "strange_share": k["strange_share"],
        "candidates_per_set": colorize.CANDIDATES,
        "colorize_geometry": {
            "resolution": list(colorize.RESOLUTION),
            "supersample": colorize.SUPERSAMPLE,
        },
        "release_geometry": k["release_record"]["geometry"],
        "autolevel": {"switch": "on" if _autolevel_on() else "off"},
        "heads": _head_stamps(),
    }

    gate_path, _, gate_new = records.write_decisions(records.GATE, run, gate_rows)
    release_path, _, release_new = records.write_decisions(records.RELEASE, run, release_rows)
    population_path, _, _ = records.write_population(
        run,
        records.population(
            run=run,
            ledgers=k["ledgers"] or ["artifacts/**/walk.jsonl"],
            counts=counts,
            cuts=cuts,
            config=config,
        ),
    )

    by_candidate = {row["candidate"]: row for row in release_rows}
    page = sheet.build(
        run,
        [by_candidate[i] for i in sorted(chosen) if i in by_candidate],
        [
            row
            for row in sorted(release_rows, key=lambda r: -(r["scores"]["p_ge3"] or 0))
            if row["verdict"] == "passed_over" and row["candidate"] not in skipped
        ][: max(6, len(chosen))],
        [row for row in release_rows if row["candidate"] in skipped],
        {
            "requested": k["n"],
            "scored": len(scored),
            "attempts": len(rows),
            "released": len(released),
            "look cap": floors.CLUSTER_CAP,
            "junk floor": floors.JUNK_FLOOR,
            "good floor": floors.GOOD_FLOOR,
            "seed": k["seed"],
        },
        directory,
        directory / f"release_sheet_{run}.html",
    )

    summary = {
        "schema": records.SCHEMA,
        "run": run,
        "seconds": round(k["seconds"], 1),
        "counts": counts,
        "supply": k["supply"],
        "budget": k["budget_record"],
        "realized_fills": k["realized"],
        "selection": k["split"],
        "release": k["release_record"],
        "cuts": cuts,
        "config": config,
        "records": {
            "durable": records.is_durable(),
            "root": str(records.root()),
            "gate": f"{gate_path} (+{gate_new})",
            "release": f"{release_path} (+{release_new})",
            "population": str(population_path),
        },
        "sheet": str(page),
        "run_dir": str(directory),
    }
    records.write_run(run, summary)
    k["log"](f"[records] sheet {page}")
    return summary


def _release_stamps(directory: Path) -> dict:
    """The stamp each full-resolution render got, keyed by candidate."""
    path = directory / "release" / "autolevel_stamps.jsonl"
    if not path.is_file():
        return {}
    return {
        row["id"]: row["autolevel"]
        for row in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def _autolevel_on() -> bool:
    from fractal_wallpapers.coloring import autolevel

    return autolevel.enabled()


def _head_stamps() -> dict:
    """Which artifact each judge in this run actually was."""
    out = {}
    for head in ("location", "palette", *budget_module.HEADS):
        try:
            out[head] = floors.live_stamp(head)[:16]
        except floors.HeadStampMismatch as missing:
            out[head] = f"unshipped: {missing}"
    return out


__all__ = [
    "RELEASE_RESOLUTION",
    "RELEASE_SUPERSAMPLE",
    "STRANGE_SHARE",
    "curate",
    "run_dir",
]
