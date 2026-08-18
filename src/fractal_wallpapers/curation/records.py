"""What a release run leaves behind, and where a throwaway run leaves it instead.

Curation decides twice — which coloured candidates are worth keeping, and which
kept candidate takes one of the release's slots — and both decisions are taken
against a population that will not exist again. The pictures are regenerable; the
*population* is not. A run over ledgers that have since grown, through heads that
have since been re-shipped, cannot be re-run to recover what it decided, and the
rate anybody later wants to compute has the deleted denominator in it.

So the decisions accumulate here, in the durable tree, as flat one-row records:
the verdict **and** the complete join on one line — the location with every family
constant, the mode, the map, the recipe, the scores, the slot's own provenance,
the autolevel stamp of the render the decision was taken on. A row keyed on an
identifier whose meaning lives in another file is orphaned the day that file
moves.

**Passed-over rows are recorded too**, and that is the half that is easy to skip.
A record of what shipped can count what passed and never learn what it passed
*out of*, which is exactly the shape of every question about a release that is
worth asking later.

## A file per run per partition, and one reader over all of them

Both decision stores are trees — `gate/<run>/<partition>.jsonl` and
`release/<run>/<partition>.jsonl` — rather than one file each. Neither axis is
invented for the filesystem's sake. The row key already carries the run, a re-run
only ever rewrites its own rows and a second run only ever adds; and the partition
is the axis every apportionment in this project is taken on, so it is the axis the
rows already arrive in blocks of. `data/palette_choice/rows/` is written the same
way for the same reason, down to the file names.

What this buys is a ceiling that does not move with the project's age. Accumulated
into one file per stage, `release.jsonl` reached 918 KiB against the 1 MiB history
guard by the third run — a build that fails partway through a fourth. One file per
run alone would not have been enough either: the 240-attempt run that followed
wrote 828 KiB of release rows, the same squeak-under one run later. Per run *and*
partition the largest file that run wrote is 195 KiB, and a run five times its
size still fits.

[`read_decisions`] is the unified reader and the only thing a consumer needs: it
hands back the whole store in key order, exactly as the single file did, and a
caller that names a run reads that run's directory alone.

## One ephemeral flag, and it moves the whole store

A smoke run writes real rows. They upsert by key and the key carries the run id,
so a throwaway run does not corrupt an existing row — it **adds** rows, and a
sixty-row rehearsal's decisions are indistinguishable in the accumulated file from
a real release's. That is worse than it sounds, because the file exists so a later
calibration pass can read a bar's precision off accumulated releases.

[`use`] redirects the whole store to a scratch root, and [`assert_isolated`] is
the assertion a run makes **before its first write**. One binding at the run's
entry point rather than a flag at each write site, because a redirect applied at
three of four sites is not a redirect.

## A row that took a slot and has no picture is not a released row

The release verdict answers one question — is there a wallpaper at the end of this
row — so a row whose full-resolution render was killed reads [`KILLED`] and has its
picture pointer cleared, rather than reading `released` and pointing at the
candidate JPEG the gate decision was taken on. That is not a cosmetic difference:
the candidate render is a 640x360 thumbnail, it is on disk, and it resolves, so
every listing downstream would have served it as the wallpaper. run3 released 39
rows, made 37 pictures, and shipped two links to a thumbnail before anybody
noticed. [`served`] therefore asks for the picture as well as the verdict.

Unlike a rejection, this is not a verdict added after the fact by a person: it is
what the run itself decided, written by the run, and a re-run that makes the
picture flips the row back through the same upsert.

## A verdict taken after the run is added to the row, never written over it

A release can be wrong, and it is a person who finds out. When that happens the
row keeps `verdict: released` — that *is* what the run decided, and a store that
edited it would lose the only evidence the release path had a defect — and gains
a [`rejected`] block saying who rejected it, when, and against what. Scores are
untouched, nothing is deleted, and [`served`] is what every listing reads instead
of the raw verdict.

The block outlives a re-record. `_upsert` carries it forward when a fresh run of
the same name writes the same key without one, because the alternative is that
re-running a curation silently un-rejects rows a person rejected by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: The schema every record row carries.
SCHEMA = 1

#: The two decisions a run records.
GATE = "gate"
RELEASE = "release"

#: The three verdicts a release decision can carry. A row is `released` when it
#: took a slot **and** the picture for that slot exists; `killed` when it took the
#: slot and the full-resolution render died under it; `passed_over` when it took
#: no slot at all.
#:
#: `killed` is its own verdict rather than an annotation on `released` because the
#: two are answers to the same question — is there a wallpaper at the end of this
#: row — and the whole point of the record is that a reader can take the verdict
#: at face value. run3 released 39 rows and made 37 pictures; the two rows the
#: hung-unit backstop killed read `released` and pointed at the candidate JPEG the
#: gate decision was taken on, which is a 640x360 thumbnail of a wallpaper that
#: does not exist.
RELEASED, KILLED, PASSED_OVER = "released", "killed", "passed_over"

#: What a killed row says for itself, in the same one-spelling discipline as
#: [`REASONS`]. Not a member of that mapping: those are the ways a candidate loses
#: a slot, and this row won its slot — what it lost was the render.
KILLED_REASON = "the release render was killed at its deadline and no picture was made"

#: The sentence a decision row gives for each way a candidate can lose a slot to
#: something other than its own score. One spelling, here, because the sheet
#: re-derives the sections of a run it did not make by reading these back.
REASONS = {
    "cluster_cap": "a third picture of a look already taken twice",
    "below_bar": "below the acting release bar for this head",
}

_ROOT: Path | None = None


def default_root() -> Path:
    """The durable store: tracked text, accumulating across runs."""
    return repo_root() / "data" / "curation"


def scratch_root(run: str) -> Path:
    """Where a throwaway run's records go instead — under the ignored tree.

    Keyed by run, unlike the durable store, because these files accumulate *by
    run*: two rehearsals sharing a root would upsert into each other's record and
    the second one's readout would be over a population it did not produce.
    """
    return repo_root() / "scratch" / "curation" / str(run)


def use(root: Path | None = None) -> None:
    """Bind this process's record root. `None` restores the durable store."""
    global _ROOT
    _ROOT = None if root is None else Path(root).resolve()


def is_durable() -> bool:
    """True when nothing is bound — writes go to the tracked store."""
    return _ROOT is None


def root() -> Path:
    return default_root() if _ROOT is None else _ROOT


def partition_file(partition: str | None) -> str:
    """The file name one partition's rows are written under.

    `:` is not legal in a Windows path, so the separator in `julia:mandelbrot`
    becomes an underscore — the same rule, and the same resulting names, as the
    palette head's per-partition corpus under `data/palette_choice/rows/`.
    """
    return f"{str(partition or 'unpartitioned').replace(':', '_')}.jsonl"


def decisions_dir(stage: str, run: str | None = None) -> Path:
    """`<stage>`, holding every run's decisions, or `<stage>/<run>` for one run's."""
    where = root() / str(stage)
    return where if run is None else where / str(run)


def decisions_path(stage: str, run: str, partition: str | None) -> Path:
    """Where one run's decisions for one partition at one stage live."""
    return decisions_dir(stage, run) / partition_file(partition)


def sinks(run: str) -> dict:
    """Everywhere a run may write. The complete set, so the isolation check sees it all.

    The two decision entries are the run's own **directories**. A run owns every
    file under its directory and no other run writes there, which is the property
    that makes rewriting the whole thing on a re-run safe.
    """
    where = root()
    return {
        "gate": decisions_dir(GATE, run),
        "release": decisions_dir(RELEASE, run),
        "runs": where / "runs.jsonl",
        "run_record": where / "runs" / f"{run}.json",
    }


class NotIsolated(RuntimeError):
    """A run declared ephemeral resolved a record path inside the tracked tree."""


def assert_isolated(run: str) -> list[Path]:
    """Raise unless every sink is outside `data/`. Returns the sinks on success.

    Returned rather than merely checked, because an isolation claim nobody can
    read is the same shape as no isolation.
    """
    tracked = (repo_root() / "data").resolve()
    offenders = []
    for path in sinks(run).values():
        try:
            path.resolve().relative_to(tracked)
        except ValueError:
            continue
        offenders.append(path)
    if offenders:
        raise NotIsolated(
            f"this run is declared ephemeral but {len(offenders)} of its records resolve "
            f"under data/: {[str(p) for p in offenders]}. The stores accumulate by run id, so "
            f"a rehearsal does not overwrite a row — it adds rows a later calibration pass "
            f"cannot tell from a real release's. Point --record-root at a scratch path, or "
            f"drop --ephemeral and write the durable store deliberately."
        )
    return sorted(sinks(run).values())


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def decision(
    *,
    run: str,
    stage: str,
    candidate: str,
    verdict: str,
    row: dict,
    reason: str | None = None,
    slot_source: str | None = None,
    group: str | None = None,
    picture: str | None = None,
) -> dict:
    """One decision, carrying the whole join it was taken on.

    `verdict`      at the gate, `kept` or `dropped`; at the release, one of
                   [`RELEASED`], [`KILLED`] or [`PASSED_OVER`].
    `slot_source`  which kind of slot a released row took — `guarantee` or `mix`.
                   `None` on every gate row and every passed-over row: a row that
                   took no slot has no slot provenance, and defaulting it to
                   `mix` would invent a decision that was never made.
    `reason`       why, in the cases the score alone does not say. A render that
                   failed is a decision with a reason and **no score**; recording
                   it as a zero would make a crash indistinguishable from a bad
                   wallpaper.
    """
    return {
        "schema": SCHEMA,
        "key": f"{run}|{stage}|{candidate}",
        "run": run,
        "stage": stage,
        "candidate": candidate,
        "verdict": verdict,
        "reason": reason,
        "slot_source": slot_source,
        "group": group,
        "picture": picture,
        "location": {
            "key": row.get("key"),
            "partition": row.get("partition"),
            "family": row.get("family"),
            "viewport": row.get("viewport"),
            "maxiter": row.get("maxiter"),
            "ledger": row.get("ledger"),
        },
        "recipe": {
            "mode": row.get("mode"),
            "mode_kind": row.get("mode_kind"),
            "curve": row.get("curve"),
            "colormap": row.get("colormap"),
            "mirror": row.get("mirror"),
            "render": row.get("render"),
        },
        "palette": {
            "anchor": row.get("anchor"),
            "candidates": row.get("candidates"),
            "scores": row.get("candidate_scores"),
        },
        "scores": {
            "head": row.get("head"),
            "location_p_ge3": row.get("location_score"),
            "p_ge2": row.get("p_ge2"),
            "p_ge3": row.get("p_ge3"),
            "p_ge4": row.get("p_ge4"),
            "rank_score": row.get("rank_score"),
        },
        # Exactly one of these two is present on a scored row, and which one says
        # whether this head's release cut acts. An advisory annotated and removed
        # nothing; a bar decided whether the row could be seated at all, and
        # carries the height and the artifact that height lives on.
        "advisory": row.get("advisory"),
        "bar": row.get("bar"),
        # A verdict taken after the run, by a person, on a row the run released.
        # `None` on everything the review has not touched.
        "rejected": row.get("rejected"),
        "autolevel": row.get("autolevel"),
        "error": row.get("error"),
    }


# --------------------------------------------------------------------------- #
# What a run serves, once a review has been over it.
# --------------------------------------------------------------------------- #
def rejection(*, rejector: str, date: str, reason: str, note: str, bar: dict | None) -> dict:
    """The block a post-run review adds to a released row it is taking back.

    `rejector` is who — a person or the named review that stands for one — and
    `date` is when, both required, because an unattributed retraction is
    indistinguishable from a bug in the release path. `bar` is the cut the row
    failed, carried whole so the rejection can be restated against the same
    artifact after the head moves.
    """
    return {
        "rejector": str(rejector),
        "date": str(date),
        "reason": str(reason),
        "note": str(note),
        "bar": bar,
    }


def is_rejected(row: dict) -> bool:
    """Whether a later review took this row back."""
    return bool(row.get("rejected"))


def served(rows) -> list[dict]:
    """The rows a run actually serves, in candidate order.

    Released, minus what a review rejected, minus anything with no release picture
    to serve. **This, not `verdict == "released"`, is what a listing reads.** The
    raw verdict is what the run decided and it stays true; the served set is what a
    person would find at the end of a link, and the two come apart the moment
    anybody reviews a release.

    The picture is the third condition and it is not redundant with the verdict.
    A row whose render was killed is recorded as [`KILLED`] with its pointer
    cleared, so both halves of that row say the same thing — but the set this
    function names is "rows with a wallpaper at the end of them", and a set defined
    on the verdict alone would be one schema change away from serving a link to
    nothing.
    """
    return sorted(
        (
            row
            for row in rows
            if row.get("verdict") == RELEASED and row.get("picture") and not is_rejected(row)
        ),
        key=lambda row: str(row.get("candidate")),
    )


def population(*, run: str, ledgers, counts: dict, cuts: dict, config: dict) -> dict:
    """The population a run's decisions were taken out of — the denominator half.

    `counts` is the whole funnel, every stage's denominator and not just the
    survivors. Without it a later reader can count what passed and never learn
    what it passed out of.
    """
    return {
        "schema": SCHEMA,
        "key": str(run),
        "run": str(run),
        "ledgers": [str(path) for path in ledgers],
        "counts": dict(counts),
        "cuts": dict(cuts),
        "config": dict(config),
        "durable": is_durable(),
    }


def _carry(previous: dict | None, row: dict) -> dict:
    """The incoming row, keeping any review verdict the stored one already had.

    The one thing an upsert does not overwrite. A re-run re-derives every field on
    this row from the same inputs and would re-derive the rejection as absent,
    because the rejection was never one of its inputs — a person was. Silently
    un-rejecting a row a person took back is the failure this prevents.
    """
    if previous and previous.get("rejected") and not row.get("rejected"):
        return {**row, "rejected": previous["rejected"]}
    return row


def _upsert_file(path: Path, rows) -> tuple[int, int]:
    """Merge `rows` into one flat file by key, rewritten in key order. `(total, new)`.

    What `runs.jsonl` is written with. It takes a row per run rather than a run's
    worth of rows, so it has no reason to be anything but one file.
    """
    merged: dict = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing = json.loads(line)
                merged[existing["key"]] = existing
    before = set(merged)
    for row in rows:
        merged[row["key"]] = _carry(merged.get(row["key"]), row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(merged[key], ensure_ascii=False) + "\n" for key in sorted(merged)),
        encoding="utf-8",
        newline="\n",
    )
    return len(merged), len(set(merged) - before)


def _upsert(directory: Path, rows) -> tuple[int, int]:
    """Merge `rows` into one run's decision directory by key. `(total, new)`.

    The whole directory is rewritten from the merge rather than only the file a row
    happens to land in, because a row that changed partition between two runs of
    the same name would otherwise be written twice and read twice. Every file is in
    key order, and a partition left with no rows loses its file, so the listing is
    always the partitions the run actually decided in.

    Idempotent on an unchanged run — a re-run writes byte-identical output. Rows
    are only ever added or replaced by their own run, and since a run owns its
    directory outright there is nothing else in there to drop.
    """
    merged: dict = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing = json.loads(line)
                    merged[existing["key"]] = existing
    before = set(merged)
    for row in rows:
        merged[row["key"]] = _carry(merged.get(row["key"]), row)

    written: dict = {}
    for key in sorted(merged):
        row = merged[key]
        name = partition_file((row.get("location") or {}).get("partition"))
        written.setdefault(name, []).append(row)
    directory.mkdir(parents=True, exist_ok=True)
    for name, part in sorted(written.items()):
        (directory / name).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in part),
            encoding="utf-8",
            newline="\n",
        )
    for stale in directory.glob("*.jsonl"):
        if stale.name not in written:
            stale.unlink()
    return len(merged), len(set(merged) - before)


def write_decisions(stage: str, run: str, rows) -> tuple[Path, int, int]:
    directory = sinks(run)["gate" if stage == GATE else "release"]
    total, new = _upsert(directory, rows)
    return directory, total, new


def write_population(run: str, row: dict) -> tuple[Path, int, int]:
    path = sinks(run)["runs"]
    total, new = _upsert_file(path, [row])
    return path, total, new


def write_run(run: str, record: dict) -> Path:
    """The run's own summary, one file, whole. Not upserted: a re-run replaces it."""
    path = sinks(run)["run_record"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _rows_of(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def read_decisions(stage: str, run: str | None = None) -> list[dict]:
    """Every recorded decision at `stage`, optionally for one run.

    **This is the unified reader, and it is the only thing a consumer needs.** The
    rows live a file per run per partition and this hands back the whole store in
    key order regardless — the same list, in the same order, that a single
    accumulated file gave. A caller that named a run reads that run's directory; a
    caller that did not reads every one of them, so a store spread over many files
    is still one logical store.

    The read side exists because a record nothing can get at without parsing by
    hand is a record nobody will read.
    """
    directory = decisions_dir(stage, run)
    if not directory.is_dir():
        return []
    rows = [
        row
        for path in sorted(directory.glob("*.jsonl" if run is not None else "*/*.jsonl"))
        for row in _rows_of(path)
        if run is None or row["run"] == run
    ]
    return sorted(rows, key=lambda row: str(row["key"]))


__all__ = [
    "GATE",
    "KILLED",
    "KILLED_REASON",
    "PASSED_OVER",
    "REASONS",
    "RELEASE",
    "RELEASED",
    "SCHEMA",
    "NotIsolated",
    "assert_isolated",
    "decision",
    "decisions_dir",
    "decisions_path",
    "partition_file",
    "default_root",
    "is_durable",
    "is_rejected",
    "population",
    "read_decisions",
    "rejection",
    "root",
    "scratch_root",
    "served",
    "sinks",
    "use",
    "write_decisions",
    "write_population",
    "write_run",
]
