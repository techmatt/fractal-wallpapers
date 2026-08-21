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

## A long run is sized by a clock as well as by `-n`

`--wall-budget` hands the run to [`pacing`], which gates every colorize attempt
and every release render *before* it starts and stops cleanly at the boundary
where it cannot afford the next one. Stopping is an outcome, not a failure: the
summary says `budget_stopped`, which is a different thing from `completed` and a
different thing again from `crashed`, and a short release is attributable to the
clock instead of being mistaken for thin supply.

## A run is bound to its supply, once

Which ledgers this release is drawn from is part of the plan, not a flag each
stage carries: it is declared at the run's entry — as ledgers, or as the harvest
run that fed it — resolved, written into `run_plan.json`, and read from there by
the intake and by everything the intake feeds. There is no "all of them" default
anywhere in the path. A run that could reach every ledger under `artifacts/`
because a flag was forgotten is a run whose funnel is printed over two harvests'
supply, and nothing about the numbers looks wrong.

## An interrupted run is continued, not restarted

`--resume` reads the run's own sidecars — the candidate log for the colorize, the
pictures on disk for the release — and skips what is already finished. Two rules
make that safe. The plan is **not re-derived from the command line**: it is read
back out of `run_plan.json`, written at the run's entry, so a resume cannot
quietly re-plan a run half of whose attempts are already recorded. And nothing
half-written is trusted — a torn last row, a picture whose render was killed
mid-write, a field whose record never landed are discarded and made again.

The seam is checked rather than asserted: `planned = resumed + made + failed +
not-started` on both legs, and a run that cannot balance those says so loudly and
exits non-zero.

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

That rule now has an enforcing edge on one head. The strange judge's release cut
**acts** ([`floors.STRANGE_RELEASE_BAR`]): a strange row below it is not seated
under any supply condition, and a strange slot with nothing above it goes
*unfilled*. The release target is a cap and not a quota, and the run summary
reports planned against seated against unfilled per head and per partition so a
short release is attributable to the bar rather than mistaken for thin supply.
The smooth judge's cut still only annotates.
"""

from __future__ import annotations

import json
import shutil
from contextlib import contextmanager
from pathlib import Path

from fractal_wallpapers.curation import (
    binding,
    colorize,
    floors,
    intake,
    pacing,
    records,
    release,
    selection,
    sheet,
)
from fractal_wallpapers.curation import (
    budget as budget_module,
)
from fractal_wallpapers.paths import tracked_name, under

#: The share of a release's slots the strange judge fills. Half, which is a
#: policy about what a release looks like and not a measurement — the two judges
#: cover disjoint sets of colorings and neither is the point of the project on
#: its own.
STRANGE_SHARE = 0.5

#: The shape of a run, when the caller did not say. Here rather than on the
#: command line because a resumed run takes its shape from its own sidecar, and
#: two sets of defaults is how the sidecar and the flag come to disagree.
DEFAULT_N = 6
DEFAULT_SEED = 0

#: What a release picture is rendered at.
RELEASE_RESOLUTION = (2560, 1440)
RELEASE_SUPERSAMPLE = 4

#: The schema of the sidecar that fixes a run's shape at its entry.
PLAN_SCHEMA = 1

#: The parameters that decide *what a run makes*. Fixed once, at the run's entry,
#: and read back rather than re-derived on a resume: everything else — workers,
#: device, the wall budget — changes how the same plan is executed and may
#: legitimately differ between the interrupted run and the one continuing it.
SHAPE = ("n", "seed", "strange_share", "attempts", "ledgers", "ephemeral")


class RunRefused(RuntimeError):
    """A run cannot start or continue as asked, and guessing would cost records."""


def run_dir(run: str) -> Path:
    """Where a run's pictures and caches live. Ignored, and regenerable."""
    return under("curation", "runs", str(run))


def curate(
    run: str,
    n: int | None = None,
    seed: int | None = None,
    strange_share: float | None = None,
    attempts: int | None = None,
    workers: int = release.DEFAULT_WORKERS,
    ephemeral: bool = False,
    ledgers=None,
    device: str = "auto",
    skip_release: bool = False,
    wall_budget: float | None = None,
    ceilings: dict | None = None,
    resume: bool = False,
    log=print,
) -> dict:
    """One release, end to end. Returns the run's own summary record.

    The shape parameters are `None` for "whatever this run's shape already is" —
    the defaults on a fresh run, the sidecar's own values on a resumed one — so
    that a resume cannot re-plan a run by omitting a flag.

    `ceilings` is not one of them. It says how long a unit may take before it is
    killed, which is *execution* rather than shape — the same kind of fact as the
    worker count and the wall budget — so a resume may legitimately carry a
    different set. [`fractal_wallpapers.deep.run.HUNG_CEILING`] is the one other
    set that exists, and the clock records whichever was used.
    """
    clock = pacing.Clock(wall_budget, ceilings=ceilings)
    directory = run_dir(run)
    directory.mkdir(parents=True, exist_ok=True)
    shape = _shape(
        directory,
        run,
        resume,
        {
            "n": n,
            "seed": seed,
            "strange_share": strange_share,
            "attempts": attempts,
            "ledgers": ledgers,
            "ephemeral": ephemeral or None,
        },
        log,
    )
    n, seed, strange_share = shape["n"], shape["seed"], shape["strange_share"]
    attempts, ledgers = shape["attempts"], shape["ledgers"]
    log(f"[intake] bound to {len(ledgers)} ledger(s): {', '.join(ledgers)}")

    if shape["ephemeral"]:
        records.use(records.scratch_root(run))
        log(f"[records] ephemeral: {records.root()}")
        records.assert_isolated(run)
    else:
        records.use(None)
        log(f"[records] durable: {records.root()}")
    if wall_budget is not None:
        log(f"[budget] wall budget {wall_budget:.0f}s, margins {clock.margins}")

    with _state(directory, run, clock) as state:
        # --- intake ------------------------------------------------------ #
        offer, supply = intake.ranked(ledgers)
        for line in intake.supply_lines(supply):
            log(f"[intake] {line}")
        claims = intake.guaranteed(supply)
        caps = intake.emit_caps(offer)
        log(f"[intake] {intake.funnel_line(supply)}")
        log(f"[intake] {len(claims)} partition(s) owed a guaranteed slot")
        by_key = {row["key"]: row for rows in offer.values() for row in rows}

        # --- budget ------------------------------------------------------ #
        plan, budget_record = budget_module.plan(
            offer, n, strange_share, budget=attempts, guarantees=claims
        )
        for line in budget_module.fill_lines(budget_record, {}):
            log(f"[budget] {line}")

        # --- colorize ---------------------------------------------------- #
        rows, colorize_counts = _colorize(directory, plan, by_key, seed, device, resume, clock, log)
        scored = [row for row in rows if row.get("p_ge3") is not None]
        realized = budget_module.realized(scored)
        for line in budget_module.fill_lines(budget_record, realized):
            log(f"[budget] {line}")

        # --- selection --------------------------------------------------- #
        selected, log_rows, split = _select(scored, n, strange_share, caps, claims, log)

        # --- release ----------------------------------------------------- #
        released, release_record = _release(
            selected, by_key, directory, workers, skip_release, log, clock.leg(pacing.RELEASE)
        )

        # --- the seam ---------------------------------------------------- #
        reconciliation = _reconcile(colorize_counts, release_record, log)
        state["outcome"] = "budget_stopped" if clock.stopped() else "completed"

        # --- records ----------------------------------------------------- #
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
            seconds=clock.elapsed(),
            outcome=state["outcome"],
            wall=clock.record(),
            colorize_counts=colorize_counts,
            reconciliation=reconciliation,
            log=log,
        )
    records.use(None)
    return summary


# --------------------------------------------------------------------------- #
# The shape of a run, and the state it is in.
# --------------------------------------------------------------------------- #
def _shape(directory: Path, run: str, resume: bool, given: dict, log) -> dict:
    """Fix what this run makes, once, and write it down. `--resume` reads it back.

    A resumed run that re-derived its plan from the command line would be one
    forgotten flag away from colorizing a different set of locations into the same
    candidate log — and the log is keyed by attempt index, so the two would
    interleave rather than collide. Hence the sidecar, and hence a *refusal*
    rather than a warning when a flag contradicts it.
    """
    path = directory / "run_plan.json"
    # Resolved before anything is compared or written, so the plan records the
    # binding rather than the flags that implied it — and so a resume whose
    # --ledger spells the same file differently is not read as a second shape.
    given = dict(given)
    if given["ledgers"] is not None:
        given["ledgers"] = [binding.label(p) for p in binding.resolve(given["ledgers"])]
    if resume:
        if not path.is_file():
            raise RunRefused(
                f"there is no run plan at {path}, so run {run!r} was never started here and "
                f"there is nothing to resume. Start it with --run {run}."
            )
        stored = json.loads(path.read_text(encoding="utf-8"))
        conflicts = {
            key: (given[key], stored.get(key))
            for key in SHAPE
            if given.get(key) is not None and stored.get(key) != given[key]
        }
        if conflicts:
            raise RunRefused(
                f"run {run!r} was planned with {_shape_line(stored)} and the flags given say "
                f"{conflicts}. Resuming with a different shape would write a second plan's "
                f"attempts into the first plan's log. Drop the flag to continue the run as "
                f"planned, or start a new run under another name."
            )
        log(f"[resume] plan from {path}: {_shape_line(stored)}")
        log(f"[resume] the interrupted run ended: {_previous(directory)}")
        return stored
    if path.is_file():
        raise RunRefused(
            f"run {run!r} already has a plan at {path}. Continuing it is a decision, not a "
            f"default: pass --resume {run} to carry on from what it finished, or choose "
            f"another --run name to start a fresh one."
        )
    shape = {
        "schema": PLAN_SCHEMA,
        "run": str(run),
        "n": DEFAULT_N if given["n"] is None else int(given["n"]),
        "seed": DEFAULT_SEED if given["seed"] is None else int(given["seed"]),
        "strange_share": (
            STRANGE_SHARE if given["strange_share"] is None else float(given["strange_share"])
        ),
        "attempts": None if given["attempts"] is None else int(given["attempts"]),
        # Never `None`: a run declares its supply at its entry, and the one case
        # resolution settles without being told — the only ledger there is — is
        # still written down, because next month there will be two.
        "ledgers": [binding.label(p) for p in binding.resolve(given["ledgers"])],
        "ephemeral": bool(given["ephemeral"]),
    }
    path.write_text(json.dumps(shape, indent=2) + "\n", encoding="utf-8", newline="\n")
    return shape


def _shape_line(shape: dict) -> str:
    """The shape of a run in one line, for a message that has to be read."""
    return ", ".join(f"{key}={shape.get(key)!r}" for key in SHAPE)


def _previous(directory: Path) -> str:
    """How the last attempt at this run ended, off its own state file."""
    path = directory / "state.json"
    if not path.is_file():
        return "no state recorded (it never wrote one)"
    state = json.loads(path.read_text(encoding="utf-8"))
    outcome = state.get("outcome")
    if outcome == "running":
        return "crashed or was killed - it never recorded an ending"
    return f"{outcome} ({state.get('error') or 'no error'})"


@contextmanager
def _state(directory: Path, run: str, clock):
    """Record what this attempt at the run is doing, and how it stopped.

    Written before the first record and rewritten after the last one, so a run
    that was killed leaves `running` behind and the resume that follows can say
    so. The three endings are distinct on purpose: `budget_stopped` is a run that
    did what it was told, and reporting it as either `completed` or `crashed`
    loses the only fact that explains a short release.
    """
    path = directory / "state.json"
    state = {"schema": PLAN_SCHEMA, "run": str(run), "outcome": "running"}

    def write() -> None:
        state["elapsed"] = round(clock.elapsed(), 1)
        state["wall_budget"] = clock.budget
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")

    write()
    try:
        yield state
    except BaseException as failure:  # a kill is an ending too, and it must be recorded
        state["outcome"] = "crashed"
        state["error"] = repr(failure)[:400]
        write()
        raise
    write()


# --------------------------------------------------------------------------- #
# The colorize leg: gated, resumable, and never trusting a half-written picture.
# --------------------------------------------------------------------------- #
def _colorize(directory: Path, plan, by_key, seed, device, resume, clock, log):
    """Make every attempt the plan asks for that this run has not already made.

    Returns `(rows, counts)` — every row the run has, resumed and fresh together,
    and the four numbers the seam is reconciled from.
    """
    candidate_log = directory / "candidates.jsonl"
    done = _completed(candidate_log, log)
    if resume:
        log(f"[resume] {len(done)} of {len(plan)} attempt(s) already recorded")
        _discard_partials(directory, len(plan), done, log)
    leg = clock.leg(pacing.COLORIZE)
    picked = colorize.anchors(colorize.pool(), len(plan), seed)
    rows = list(done.values())
    counts = {"planned": len(plan), "resumed": len(done), "made": 0, "failed": 0, "killed": 0}
    # Built on the first attempt this run actually makes, not before: loading three
    # heads to discover that everything is already done, or that the clock has no
    # room for an attempt, is the setup cost of a run that does no work.
    colorizer = None
    stopped_at = None

    for index, attempt in enumerate(plan):
        if index in done:
            continue
        decline = leg.may_start()
        if decline is not None:
            stopped_at = index
            log(f"[colorize] BUDGET STOP before attempt {index}: {decline}")
            break
        if colorizer is None:
            colorizer = colorize.Colorizer(directory, seed, device, log)
        with leg.unit() as unit:
            row = colorize.annotate(
                colorizer.attempt(attempt, by_key[attempt.key], picked[index], index)
            )
            unit.ok = row.get("p_ge3") is not None
        row["timed_out"] = unit.expired
        rows.append(row)
        _append(candidate_log, row)
        counts["made" if unit.ok else "failed"] += 1
        counts["killed"] += int(unit.expired)
        verdict = (
            f"P(>=3) {row['p_ge3']:.4f}"
            if row.get("p_ge3") is not None
            else f"{'KILLED' if unit.expired else 'FAILED'} {row.get('error')}"
        )
        log(
            f"[colorize] {index + 1}/{len(plan)} {attempt.head} {attempt.partition} "
            f"{row.get('mode')}/{row.get('colormap')} {verdict} {unit.seconds:.1f}s"
        )

    counts["not_started"] = (
        0 if stopped_at is None else sum(1 for i in range(stopped_at, len(plan)) if i not in done)
    )
    rows.sort(key=lambda row: row["attempt"])
    return rows, counts


def _append(path: Path, row: dict) -> None:
    """One candidate row onto the log. The one write that makes an attempt done."""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _completed(path: Path, log) -> dict:
    """Attempts already made, by index, with a torn tail dropped and the file repaired.

    A run killed mid-append leaves a partial last line, and a log left in that
    state is not merely one row short: the next append lands on the same line and
    the two rows become one unparseable one. So the repair is a rewrite, here,
    before anything else reads it.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict = {}
    kept, torn = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            torn += 1
            continue
        out[int(row["attempt"])] = row
        kept.append(line)
    if torn or (text and not text.endswith("\n")):
        log(f"[resume] repairing {path.name}: {torn} torn row(s) dropped, {len(kept)} kept")
        path.write_text("".join(line + "\n" for line in kept), encoding="utf-8", newline="\n")
    return out


def _discard_partials(directory: Path, planned: int, done: dict, log) -> dict:
    """Throw away everything a killed attempt may have left half-written.

    The candidate log says which attempts finished; it says nothing about what the
    one that did not was in the middle of. Three caches can hold a truncated file
    — the attempt's own picture, the recolors the palette head reads, the dumped
    field they are recolors *of* — and all three are addressed by name, so a
    half-written one is indistinguishable from a finished one at the point of use.
    Every one of them is regenerable, which makes this cheap; trusting one is not.
    """
    scrubbed = {"pictures": 0, "candidates": 0, "fields": 0, "unfinished": 0}
    for index in range(planned):
        if index in done:
            continue
        picture = directory / "pictures" / f"{index:04d}.jpg"
        leveled = directory / "pictures" / f"{index:04d}.leveled"
        if picture.is_file():
            picture.unlink()
            scrubbed["pictures"] += 1
        if leveled.is_dir():
            shutil.rmtree(leveled)
    # A render killed between its temporary and the rename leaves the temporary.
    # It is regenerable and it is never read, but a tree that accumulates them
    # across resumes is a tree nobody can size.
    scrubbed["unfinished"] = colorize.sweep_writing(directory)
    for candidate in sorted((directory / "candidates").rglob("*.jpg")):
        # `decodable` verifies the file and removes it when it cannot be read.
        # The recolors have no completion record of their own — they are named
        # for their recipe and made in one engine call — so bytes are the whole
        # question here, unlike a release row.
        if not release.decodable(candidate):
            scrubbed["candidates"] += 1
    for dumped in sorted((directory / "fields").glob("*.f32")):
        if not _intact_field(dumped):
            dumped.unlink(missing_ok=True)
            dumped.with_suffix(".json").unlink(missing_ok=True)
            scrubbed["fields"] += 1
    if any(scrubbed.values()):
        log(f"[resume] discarded partial output: {scrubbed}")
    return scrubbed


def _intact_field(path: Path) -> bool:
    """Whether a dumped field is all there, by its own record's sample count.

    The engine writes the binary first and its record second, so a record on disk
    already implies a completed write — but the field is the expensive half and
    the check that settles it is one `stat` against a number the record states.
    """
    record = path.with_suffix(".json")
    if not record.is_file():
        return False
    try:
        samples = json.loads(record.read_text(encoding="utf-8"))["samples"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return False
    return path.stat().st_size == int(samples[0]) * int(samples[1]) * 4


def _select(scored, n, strange_share, caps, claims, log):
    """Two disjoint judge passes, one look counter across both, one bar on one head.

    The allocation is solved over the partitions that have a *scored* candidate,
    not over the ones that have a candidate clearing the bar. That is deliberate
    and it is the no-redistribution rule again: a partition whose whole supply the
    bar rejects holds its slot and leaves it unfilled, because handing the slot to
    a partition that had plenty is padding one level up from the padding this bar
    exists to end.
    """
    slots = budget_module.head_slots(n, strange_share)
    by_head = {head: [row for row in scored if row["head"] == head] for head in budget_module.HEADS}
    entries = {head: selection.entries(rows) for head, rows in by_head.items()}
    owed, unplaced = budget_module.assign_guarantees(
        [p for p in claims if any(e["partition"] == p for v in entries.values() for e in v)],
        slots,
    )

    used: dict = {}
    selected, log_rows, allocations, fill = [], [], {}, {}
    for head in budget_module.HEADS:
        present = {entry["partition"] for entry in entries[head]}
        mine = {p for p, h in owed.items() if h == head and p in present}
        allocation = intake.slots(present, slots[head], mine, caps=None)
        allocations[head] = allocation
        bar = floors.release_bar(head)
        picks, rows, fills = selection.select(
            entries[head],
            allocation,
            {p: caps.get(p, 0) for p in present},
            used,
            guarantees=mine,
            bar=bar,
        )
        for row in rows:
            row["head"] = head
        selected.extend(picks)
        log_rows.extend(rows)
        fill[head] = {
            # `target` is the head's share of -n; `planned` is that share once the
            # allocation has put it on partitions, and the two differ when a head
            # has fewer supplied partitions than slots. Both, because a release
            # short at the first number and a release short at the second are
            # different failures.
            "target": int(slots[head]),
            "planned": sum(cell["planned"] for cell in fills.values()),
            "seated": len(picks),
            "unfilled": sum(cell["unfilled"] for cell in fills.values()),
            "bar": None
            if bar is None
            else {"name": bar.name, "value": bar.value, "head_sha256": bar.stamp, "acts": True},
            "by_partition": {p: fills[p] for p in sorted(fills)},
        }

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
        "below_bar_skips": sum(1 for row in log_rows if row.get("skipped") == "below_bar"),
        # Planned against seated against unfilled, per head and per partition.
        # A short release is attributable at a glance or it is read as thin
        # supply, and after a bar started acting those are no longer the same
        # thing.
        "fill": fill,
        "guarantee": {
            "owed": dict(sorted(owed.items())),
            "unplaced": list(unplaced),
            "slots_taken": sum(1 for row in log_rows if row.get("slot_source") == "guarantee"),
        },
        "short_by": max(0, n - len(selected)),
    }
    for head in budget_module.HEADS:
        cells = fill[head]
        bar = cells["bar"]
        line = (
            f"[select] {head}: {cells['planned']} planned, {cells['seated']} seated, "
            f"{cells['unfilled']} unfilled"
            + (f" · bar {bar['value']:g} ACTING" if bar else " · no acting bar")
        )
        short = {
            partition: cell["reason"]
            for partition, cell in cells["by_partition"].items()
            if cell["unfilled"]
        }
        if short:
            line += " · " + ", ".join(f"{p} {r}" for p, r in sorted(short.items()))
        log(line)
    if split["short_by"]:
        log(
            f"[select] SHORT-FILL {len(selected)}/{n}: "
            + ", ".join(
                f"{head} {split['head_selected'][head]}/{slots[head]} "
                f"(eligible {split['head_eligible'][head]})"
                for head in budget_module.HEADS
            )
            + f". Shipping fewer rather than filling past a slot, supply, look or bar cut "
            f"({split['cluster_cap_skips']} look-cap skips, "
            f"{split['below_bar_skips']} below the bar)."
        )
    log(
        f"[select] {len(selected)} selected: "
        + ", ".join(f"{head} {split['head_selected'][head]}" for head in budget_module.HEADS)
        + f"; {split['guarantee']['slots_taken']} guarantee slot(s)"
    )
    return selected, log_rows, split


def _release(selected, by_key, directory, workers, skip, log, leg=None):
    """The full-resolution pass. The parent writes every record, in plan order.

    A row this run **recorded as finished** before it was interrupted is carried
    across — selection is deterministic from the candidate log, so a resumed run
    picks the same rows — and every other row is made again. The reuse test is
    the leg's own completion record and not the file on disk, because a picture
    on disk is only evidence that a render wrote bytes: see
    [`release.completed`] for the four rows that cost.
    """
    where = directory / "release"
    where.mkdir(parents=True, exist_ok=True)
    stamps = where / "autolevel_stamps.jsonl"
    geometry = {
        "resolution": list(RELEASE_RESOLUTION),
        "supersample": RELEASE_SUPERSAMPLE,
    }
    finished = release.completed(where)
    swept = colorize.sweep_writing(where)
    if swept:
        log(f"[release] discarded {swept} unfinished render(s) left by an earlier attempt")

    tasks, done, reused = [], {}, []
    for entry in selected:
        row = entry["row"]
        identifier = entry["id"]
        picture = where / f"{identifier}.png"
        if skip or release.resumable(identifier, picture, finished):
            # Reusing a picture is only reuse when there is one. `--skip-release`
            # over a run that has never rendered leaves the row unreleased, and
            # counting it as reused would report a release that did not happen.
            if picture.is_file():
                done[identifier] = picture
                reused.append(identifier)
            continue
        # A row that is being remade must not leave its predecessor behind: the
        # renderer writes to a temporary and renames, so an old picture would
        # survive a failure and read as this attempt's work.
        picture.unlink(missing_ok=True)
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

    outcomes = {"rendered": 0, "failed": 0}

    def sink(task, result):
        """THE parent-side writer: everything durable about a release render, here."""
        outcomes["rendered" if result.ok else "failed"] += 1
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
        # Written last, and it is what a resume reads: a row is finished when the
        # parent says so, never when a file merely exists.
        with release.timing_path(where).open("a", encoding="utf-8", newline="\n") as handle:
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

    record = release.run_pass(tasks, workers, sink, log, leg=leg)
    record["reused"] = len(reused)
    record["geometry"] = geometry
    record["counts"] = {
        "planned": len(selected),
        "resumed": len(reused),
        "made": outcomes["rendered"],
        "failed": outcomes["failed"],
        "not_started": len(record["not_started"]),
    }
    # Plan order, not completion order: a concurrent pass finishes out of order
    # and everything downstream lays the pictures out in the order given here.
    return [(entry["id"], done[entry["id"]]) for entry in selected if entry["id"] in done], record


#: The four things that can happen to a planned unit, and the identity they owe
#: the plan. A resumed run is the only place these can disagree, which is exactly
#: why the check exists there and is arithmetic rather than a claim in a comment.
BUCKETS = ("resumed", "made", "failed", "not_started")


def _reconcile(colorize_counts: dict, release_record: dict, log) -> dict:
    """Balance both legs against their plans, and be loud when they do not.

    A resume that re-made a finished attempt, or skipped an unfinished one, is
    invisible in every other number a run prints: the release still ships, the
    records still upsert, the sheet still renders. It shows up here or nowhere.
    """
    out: dict = {}
    for leg, counts in (("colorize", colorize_counts), ("release", release_record["counts"])):
        total = sum(int(counts.get(name, 0)) for name in BUCKETS)
        holds = total == int(counts["planned"])
        out[leg] = {**{name: int(counts.get(name, 0)) for name in BUCKETS}, "holds": holds}
        out[leg]["planned"] = int(counts["planned"])
        line = " + ".join(f"{out[leg][name]} {name}" for name in BUCKETS)
        if holds:
            log(f"[reconcile] {leg}: {counts['planned']} planned = {line}")
        else:
            log(
                f"[reconcile] MISMATCH on the {leg} leg: {counts['planned']} planned against "
                f"{line} = {total}. A unit was made twice or lost across the resume seam."
            )
    out["holds"] = all(out[leg]["holds"] for leg in ("colorize", "release"))
    return out


def release_verdict(seated: bool, picture) -> tuple[str, str | None]:
    """What a release row's verdict and reason are, given a slot and a picture.

    Three states and they are not two: a row that took no slot was passed over, a
    row that took one and has a full-resolution picture was released, and a row
    that took one and has no picture is a row whose render died under it. The last
    used to be recorded as the second, with the candidate JPEG the gate decision
    was taken on left in the picture pointer — a 640x360 thumbnail that is on disk
    and resolves, so every listing downstream served it as the wallpaper.
    """
    if not seated:
        return records.PASSED_OVER, None
    if picture is None:
        return records.KILLED, records.KILLED_REASON
    return records.RELEASED, None


def _record(**k) -> dict:
    """Write every record the run leaves behind, and return its own summary."""
    run, rows, scored, selected = k["run"], k["rows"], k["scored"], k["selected"]
    directory = k["directory"]
    released = dict(k["released"])
    chosen = {entry["id"] for entry in selected}
    group_of = {entry["id"]: entry["group"] for entry in selection.entries(scored)}
    source = {row["id"]: row.get("slot_source") for row in k["log_rows"] if row.get("picked")}
    # Every way a row lost a slot to something other than its own rank, in the
    # one spelling the sheet reads back when it rebuilds a run it did not make.
    why = {
        row["id"]: records.REASONS[row["skipped"]]
        for row in k["log_rows"]
        if row.get("skipped") in records.REASONS
    }

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
        verdict, killed = release_verdict(identifier in chosen, picture)
        # The candidate JPEG is the right pointer for a passed-over row — that
        # render is what the decision was taken on, and the sheet shows it — and
        # exactly the wrong one on a killed row, where nothing may resolve.
        decision = records.decision(
            run=run,
            stage=records.RELEASE,
            candidate=identifier,
            verdict=verdict,
            row=row,
            reason=killed or why.get(identifier),
            slot_source=source.get(identifier),
            group=group_of.get(identifier),
            picture=(
                None
                if killed
                else (str(Path(picture).relative_to(directory)) if picture else row.get("picture"))
            ),
        )
        decision["release_autolevel"] = at_release.get(identifier)
        release_rows.append(decision)

    counts = {
        # Three populations, named as three: `found` is every gate survivor,
        # `scored` is the subset the sidecar has an opinion about, and the two
        # floor counts are over `scored`. A funnel that skipped the middle number
        # invited its own rate to be read against the wrong denominator.
        "found": k["supply"]["found"],
        "scored": k["supply"]["scored"],
        "above_junk_floor": k["supply"]["passing"],
        "above_good_floor": k["supply"]["good"],
        "unscored": k["supply"]["unscored"],
        "attempts_planned": k["budget_record"]["planned"],
        "attempts_made": len(rows),
        "attempts_scored": len(scored),
        "attempts_failed": len(rows) - len(scored),
        # A resumed attempt was made by an earlier leg of the same run and a
        # not-started one was declined by the clock. Both are inside
        # `attempts_made`'s plan and neither is inside its count, so a funnel
        # without them does not add up on any run that was interrupted.
        "attempts_resumed": k["colorize_counts"]["resumed"],
        "attempts_not_started": k["colorize_counts"]["not_started"],
        "attempts_killed": k["colorize_counts"]["killed"],
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
            ledgers=k["ledgers"],
            counts=counts,
            cuts=cuts,
            config=config,
        ),
    )

    # Built from the rows as *written*, not from the rows in hand, and that is
    # the difference between one sheet generator and two. A re-recorded run keeps
    # any review verdict the store already carried ([`records._carry`]), so the
    # page a run draws and the page a rejection redraws are the same page from
    # the same function over the same rows.
    page = sheet.from_records(
        run,
        records.read_decisions(records.RELEASE, run),
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
        # `completed`, `budget_stopped` or `crashed`. First, because a reader who
        # takes one field off this record takes this one: every count below is
        # read differently depending on it.
        "outcome": k["outcome"],
        "seconds": round(k["seconds"], 1),
        "wall": k["wall"],
        "reconciliation": k["reconciliation"],
        "counts": counts,
        "ledgers": k["ledgers"],
        "supply": k["supply"],
        "budget": k["budget_record"],
        "realized_fills": k["realized"],
        "selection": k["split"],
        "release": k["release_record"],
        "cuts": cuts,
        "config": config,
        # Named through `tracked_name`, like every other path this record
        # carries: the summary is tracked, and a summary that spelled out one
        # machine's drive letter would say nothing to the machine that reads it
        # next. The run directory and its sheet are under the regenerable tree,
        # so they are named `artifacts/<rest>` and survive the tree moving tier.
        "records": {
            "durable": records.is_durable(),
            "root": tracked_name(records.root()),
            "gate": f"{tracked_name(gate_path)} (+{gate_new})",
            "release": f"{tracked_name(release_path)} (+{release_new})",
            "population": tracked_name(population_path),
        },
        "sheet": tracked_name(page),
        "run_dir": tracked_name(directory),
    }
    records.write_run(run, summary)
    k["log"](f"[records] sheet {page}")
    return summary


def _release_stamps(directory: Path) -> dict:
    """The stamp each full-resolution render got, keyed by candidate.

    Read as an upsert, last row winning: a row whose first render was killed
    mid-write and made again on a resume has two stamps in the log and only the
    second one is the picture that exists.
    """
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
    "DEFAULT_N",
    "DEFAULT_SEED",
    "PLAN_SCHEMA",
    "RELEASE_RESOLUTION",
    "RELEASE_SUPERSAMPLE",
    "release_verdict",
    "SHAPE",
    "STRANGE_SHARE",
    "RunRefused",
    "curate",
    "run_dir",
]
