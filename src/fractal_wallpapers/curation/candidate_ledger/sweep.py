"""What comes off the disk: the retention rule, and the pictures nothing names.

Two sweeps pointed in opposite directions. [`prune`] is the rule the store is
bounded by, acting on rows and taking their pictures with them; [`orphans`] is
the backstop under it, acting on pictures **no store** names at all — the ledger,
the two tracked decision stores and the kept gallery attempt rows, unioned in
[`_named_by_a_store`]. [`delete_pictures`] is the single verb both go through,
and the only place this project unlinks a candidate.

[`remove`] is beside them and is neither: a **told** removal of named rows, for a
pass that replaces a row and has to take the one it replaced. It decides nothing
and honours no protection of its own — the caller owns that list — which is what
keeps the rule in one place while the verb is available to more than one.

**The picture sweep does not write to [`ratchet`] and both row transactions do,
and the asymmetry is the point.** The ratchet is a guard over the *rows*, so
`prune` and `remove` each record what they took and the orphan sweep records
nothing: it deletes pictures a row never named, and no count the ratchet holds can
move under it. A sweep that recorded its pictures there would be handing the
census a licence to lose rows it never lost.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation.candidate_ledger import ratchet, store
from fractal_wallpapers.curation.candidate_ledger import rows as rows_module
from fractal_wallpapers.curation.candidate_ledger.store import (
    ALL_UNMERGED,
    PICTURES_NAME,
    POOL_SUBTREES,
    RETAIN_PER_PAIR,
    RETAINED_FITTED,
    RETAINED_LABELED,
    RETAINED_RANKED,
    RETAINED_REASONS,
    RETAINED_REJECTED,
    RETAINED_SEATED,
    RETAINED_TENTATIVE,
    SCHEMA,
    LedgerError,
)
from fractal_wallpapers.paths import rehome, tracked_name, under


def picture_census(rows=None) -> dict:
    """How many rows name a picture that is not there, by mode and by run.

    **Nearly always zero now, and that is the change.** While the picture rule
    ran on its own ranking at its own K this was permanent expected state, 30,040
    rows wide; since 2026-08-29 a picture is kept if and only if its row is, so a
    row naming an absent picture is either one of the 41 the ledger inherited or
    a [`prune`] that was interrupted between its two halves. Either way this is
    the reader that says so — without it the only way to notice was a seating
    behaving oddly, which is how it was in fact noticed.
    """
    stored = store.read() if rows is None else rows
    present = store.present_pictures(stored)
    by_mode: dict = {}
    by_run: dict = {}
    absent = 0
    for row in stored:
        gone = str(row["key"]) not in present
        absent += gone
        mode = str((row.get("recipe") or {}).get("mode") or "?")
        run = str((row.get("provenance") or {}).get("run") or "?")
        for table, name in ((by_mode, mode), (by_run, run)):
            seen = table.setdefault(name, {"rows": 0, "absent": 0})
            seen["rows"] += 1
            seen["absent"] += gone
    for table in (by_mode, by_run):
        for seen in table.values():
            seen["share"] = round(seen["absent"] / seen["rows"], 4) if seen["rows"] else 0.0
    return {
        "schema": SCHEMA,
        "rows": len(stored),
        "with_a_picture_on_disk": len(present),
        "naming_a_picture_that_is_absent": absent,
        "share_absent": round(absent / len(stored), 4) if stored else 0.0,
        "policy": (
            "expected: `curate retention` drops pictures and never rows. An absent "
            "picture is not damage, and `curate candidate-ledger backfill` will not "
            "bring it back — only a re-render will."
        ),
        "by_mode": dict(sorted(by_mode.items(), key=lambda item: -item[1]["absent"])),
        "by_run": dict(sorted(by_run.items(), key=lambda item: -item[1]["absent"])),
    }


def picture_dirs() -> list[Path]:
    """Every `<pool subtree>/<leg>/pictures` there is, resolved through the tiers.

    A fixed shape at a fixed depth, not a walk: the directories are named rather
    than discovered, so the enumeration cannot follow the tree into somewhere
    that merely happens to hold JPEGs.
    """
    found = []
    for name in POOL_SUBTREES:
        base = under("curation", name)
        if not base.is_dir():
            continue
        for leg in sorted(base.iterdir()):
            where = leg / PICTURES_NAME
            if where.is_dir():
                found.append(where)
    return found


def _decision_rows(tiers) -> tuple[list[dict], dict]:
    """Every decision row this project keeps, slimmed to the four fields that
    identify a picture, with `{store: rows read}` beside it.

    Three stores, and they are three because the decisions were written by three
    different things and never merged: the tracked release store, the tracked gate
    store, and the retired gallery passes' attempt rows under
    `artifacts/curation/gallery/<pass>/gate.jsonl` — 14,438 of those, kept on
    Matt's ruling of 2026-09-07 and read by nothing else in the tree.

    **Slimmed rather than read whole**, because a decision row carries its entire
    join and the attempt rows alone are 53 MB: `origin_of` reads `source`, `run`
    and `candidate` and nothing more, so those plus `key` are the whole projection
    and the rest never reaches memory.
    """
    from fractal_wallpapers.curation import records

    def slim(row: dict) -> dict:
        return {
            "key": row.get("key"),
            "run": row.get("run"),
            "candidate": row.get("candidate"),
            "source": row.get("source"),
        }

    rows: list[dict] = []
    counts: dict = {}
    for name, stage in (("release_store", records.RELEASE), ("gate_store", records.GATE)):
        read = [slim(row) for row in records.read_decisions(stage)]
        counts[name] = len(read)
        rows += read

    attempts = 0
    gallery = tiers.resolve(("curation", "gallery"))
    if gallery.is_dir():
        for pass_dir in sorted(gallery.iterdir()):
            path = pass_dir / "gate.jsonl"
            if not path.is_file():
                continue
            with path.open(encoding="utf-8") as lines:
                for line in lines:
                    if line.strip():
                        rows.append(slim(json.loads(line)))
                        attempts += 1
    counts["gallery_attempts"] = attempts
    return rows, counts


def _named_by_a_store(tiers) -> tuple[dict, set, dict]:
    """`({pictures directory: {file name}}, {directory a MERGE stamped}, {source: rows})`.

    **The reference set is the union over every store that names a picture**, not
    the candidate ledger alone, and that changed on 2026-09-07 because the older
    rule deleted work. The ledger holds `runs` by [`backfill`], which read the two
    decision stores once — so it holds what those runs *decided about* and drifts
    away from it with every prune. On 2026-09-02 the gap was 3,610 pictures: they
    were swept as garbage and `curate re-render` put 3,615 of them back the next
    morning, because the pool still named them. A sweep and a repair pointed at
    the same files is a loop, and the union is which of the two was wrong.

    Bucketed by directory and resolved through one shared [`paths.Tiers`]
    snapshot, for [`present_pictures`]'s reason: the alternative re-reads the
    settings once per row, which was 215 s against 1.0 s over this store. The
    decision rows are resolved **once per run** for the same reason — a run
    directory is a fact about the run and not about the row, and there are
    sixteen runs against seventeen thousand rows.

    **The second set is the merge stamp, the marker is [`hunt_block`], and only
    the ledger may write to it.** No leg writes a stamp of its own — `hunt.merge`,
    `mine.merge` and `depth.merge` build a report and the CLI prints it — but
    every row those three hand over carries a `hunt` block, and no other row in
    the store does. It separates exactly: of 177,993 rows on 2026-09-02, **166,118
    carry one**, which is `depth` 158,628 + `mine` 4,566 + `reframe_draw` 2,283 +
    `hunt` 641 to the row, and the 11,875 without one are the whole of `runs`.

    A decision row naming a picture is therefore **not** evidence that its leg
    merged, and folding the decision stores into the stamp would say the opposite:
    every backfilled `runs` leg would read as merged and be swept unasked, which
    is the one thing the listing exists to prevent. The union widens what is kept
    and touches nothing about which legs are decidable.
    """
    from collections import defaultdict

    from fractal_wallpapers.curation import rescore

    wanted: dict = defaultdict(set)
    stamped: set = set()
    named = 0
    for row in store.stream():
        stored = row.get("picture")
        if not stored:
            continue
        where = rehome(str(stored), tiers)
        if where is None:
            continue
        named += 1
        wanted[where.parent].add(where.name)
        if row.get("hunt") is not None:
            stamped.add(where.parent)

    decisions, reference = _decision_rows(tiers)
    reference = {"candidate_ledger": named, **reference}
    # The whole chain, and the pool is what lets it be followed: a gallery2 seat
    # of a gallery1 seat of a run9 candidate is on record, and stopping at the
    # first link names an id nothing ever made a picture of. One pool over all
    # three stores, because the chain crosses them.
    pool = {str(row["key"]): row for row in decisions if row.get("key")}
    homes: dict = {}
    for row in decisions:
        run, candidate = rescore.origin_of(row, pool)
        home = homes.get(run)
        if home is None:
            home = homes[run] = tiers.resolve(("curation", "runs", run, rescore.PICTURES))
        wanted[home].add(f"{candidate}.jpg")
    reference["pictures_named"] = sum(len(held) for held in wanted.values())
    return wanted, stamped, reference


def _unmerged_wanted(unmerged: tuple | str) -> set | str:
    """The caller's `unmerged` argument as the thing [`_is_named`] can ask about."""
    if unmerged == ALL_UNMERGED:
        return ALL_UNMERGED
    if isinstance(unmerged, str):
        raise LedgerError(
            f"{unmerged!r} is not a leg list. Pass leg names, or "
            f"candidate_ledger.ALL_UNMERGED for every one of them."
        )
    return {str(name).replace(chr(92), "/").rstrip("/") for name in unmerged}


def _is_named(leg: str, named: set | str) -> bool:
    """Whether the caller asked for this unmerged leg, by tracked name or by tail.

    Both spellings, because the listing prints the tracked name and a person
    reading it types the part that identifies the leg.
    """
    if named == ALL_UNMERGED:
        return True
    return bool(named) and (leg in named or leg.rsplit("/", 1)[-1] in named)


def orphans(apply: bool = False, unmerged: tuple | str = (), log=print) -> dict:
    """Pictures in the pool subtrees that **nothing** names. The backstop under [`prune`].

    [`prune`] is the retention rule and it runs from [`merge`], so every leg that
    finishes hands its candidates to the ledger and the rule bounds them from
    then on. A leg that is **killed** never reaches `merge`: its pictures are on
    disk, no row was ever written for them, and no later prune can free them,
    because a prune only ever decides about rows it can see. This is the only
    thing that can, and that is the whole reason it exists.

    ## What the reference set is

    **Every store that names a picture**, unioned in [`_named_by_a_store`]: the
    candidate ledger, the tracked release and gate stores, and the retired gallery
    passes' attempt rows. Not the ledger alone, which is what it was until
    2026-09-07 and what made the 09-02 sweep and `curate re-render` a loop 3,610
    pictures wide. A picture a live store still names is not garbage whatever the
    ledger has since pruned.

    Deleting the pictures behind the kept gallery attempt rows may well be right
    eventually. It is Matt's call and it is a **named act**, not a side effect of
    a garbage sweep.

    ## The merge stamp decides which question a leg is asked

    A leg that has reached `merge` has handed the ledger everything it made, so
    from that moment the **stores alone** are the reference set: a picture none of
    them names is a picture the retention rule has already decided about, and
    keeping it because the leg's own `sequence.jsonl` still mentions it is keeping
    a file against a decision rather than against an absence.

    A leg that has **not** merged is the opposite case and it is not swept **unless
    a caller names it**. Its pictures are real work with no row anywhere, which is
    precisely what this command exists for and precisely what it must not decide
    about on its own: the fix is a `merge`, which costs nothing on a partial, a
    deliberate `rm`, or this sweep pointed at it by name. Left alone, those legs
    are **skipped and listed** on the record under `unmerged`, with the count and
    the bytes each is holding, for a person to act on.

    `unmerged` is that pointing: leg names — as the listing prints them, or their
    last component — or [`ALL_UNMERGED`]. A named leg is swept **under the same
    rule as a merged one**: what a store names is kept and the rest goes. That
    is one rule rather than two, and it is why the two kinds of unmerged leg need
    no separate handling — a killed leg has no rows, so all of it goes; a
    backfilled `runs` leg keeps every picture its decision stores named and loses
    the renders nothing decided about. **That sentence is true as of 2026-09-07
    and was false while it stood**: the sweep read the ledger, and the ledger's
    copy of those decisions goes stale with every prune. The record reports them
    apart from the ordinary sweep, under `swept_unmerged`, because a person who
    named a leg should be able to read back what naming it cost.

    **The stamp is the `hunt` block, read off the ledger and not off a file** — see
    [`_named_by_a_store`], which works it out in the pass it was already making.
    Two consequences worth knowing. A leg whose every row was later pruned reads as
    unmerged and is skipped, which is the safe direction and frees nothing that is
    still there. And a leg that merged, then rendered more, then was killed has that
    tail swept — the one case the old leg-records union covered and this does not;
    `merge` it again before sweeping if that is its history.

    `store_named` on each `unmerged` entry is how to tell the two kinds apart
    without opening anything: **0** is a killed leg no store ever heard of, and
    the advice is literally re-merge or delete. A **large** number is a `runs`-era
    leg that is in the ledger by [`backfill`] and cannot be re-merged at all — its
    pictures outnumber its decisions because the decision stores were never the
    whole of what it rendered, and deleting them is a judgement about keeping a
    superseded era's attempts, not garbage collection.

    ## Where the safety actually lives

    Three places, none of them a promise made in a comment:

    * the enumeration is [`picture_dirs`], a fixed shape at a fixed depth, so a
      leg's `fields/` is not reachable however large it gets;
    * every directory is checked against the tier roots **here**, at the point of
      deciding, rather than trusted from whatever produced the list;
    * the deletion is [`delete_pictures`] and nothing else, which re-homes each
      name as it unlinks and leaves alone any name with no artifacts component.

    And the reference set is built **here**, in this call, off the stores
    themselves — never handed in and never carried over from an earlier reading.
    A sweep deciding what to unlink against a set somebody measured yesterday is
    a sweep acting on a store that has since moved.

    `apply=False` is the default and is the whole of the dry run. Costs a
    `scandir` per leg, one streamed pass of the ledger and one of each decision
    store: **9.9 s** over this store on 2026-09-02 before the union, against about
    31 s when it also read every leg's own records with a regex — that pass was
    two thirds of the run. The `reference` block on the record says what each
    store contributed.
    """
    from collections import Counter

    from fractal_wallpapers.paths import Tiers

    started = time.time()
    named = _unmerged_wanted(unmerged)
    tiers = Tiers.current()
    roots = [Path(root).resolve() for root in (tiers.hot, tiers.archive) if root is not None]
    wanted, stamped, reference = _named_by_a_store(tiers)

    by_subtree: dict = {}
    doomed: list = []
    unmerged: list = []
    swept: list = []
    unreferenced: Counter = Counter()
    for where in picture_dirs():
        # The check at the point of decision, and not carried over from the
        # enumeration. A directory that does not sit under a tier root is not
        # something this may reason about at all, whoever put it in the list.
        resolved = where.resolve()
        if not any(root == resolved or root in resolved.parents for root in roots):
            raise LedgerError(
                f"{where} is not under either tier root ({[str(root) for root in roots]}), "
                f"and this sweep deletes what it decides about. Nothing was read."
            )
        subtree = where.parent.parent.name
        cell = by_subtree.setdefault(
            subtree,
            {
                "legs": 0,
                "unmerged_legs": 0,
                "pictures": 0,
                "named_by_a_store": 0,
                "named_by_nothing": 0,
                "skipped_unmerged": 0,
                "bytes": 0,
            },
        )
        cell["legs"] += 1

        stems: dict = {}
        for entry in os.scandir(where):
            if entry.is_file(follow_symlinks=False) and entry.name.endswith(".jpg"):
                stems[entry.name] = entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False) and entry.name.endswith(".leveled"):
                # A levelled colormap whose JPEG is already gone is precisely the
                # pile, and it is addressed by the name its picture would have.
                stems.setdefault(f"{entry.name[: -len('.leveled')]}.jpg", 0)
        cell["pictures"] += len(stems)

        held = wanted.get(where, set())
        leg_name = tracked_name(where.parent)
        if where not in stamped and not _is_named(leg_name, named):
            # No merge stamp and nobody named it: the ledger has never heard of
            # this leg, so nothing here is decidable and none of it is swept.
            # Listed instead.
            cell["unmerged_legs"] += 1
            cell["skipped_unmerged"] += len(stems)
            unmerged.append(
                {
                    "leg": leg_name,
                    "pictures": len(stems),
                    "store_named": len(held),
                    "bytes": sum(stems.values()),
                    "why": "unmerged — re-merge or delete",
                }
            )
            continue
        unnamed = sorted(name for name in stems if name not in held)
        cell["named_by_a_store"] += len(stems) - len(unnamed)
        if where not in stamped:
            # Named by the caller, so swept under the merged rule — and counted
            # apart, because "you asked for this leg" and "the retention rule
            # already decided about this file" are different sentences.
            swept.append(
                {
                    "leg": leg_name,
                    "pictures": len(stems),
                    "store_named": len(held),
                    "deleting": len(unnamed),
                    "bytes": sum(stems[name] for name in unnamed),
                    "why": "unmerged, named by the caller",
                }
            )
        if not unnamed:
            continue
        unreferenced[subtree] += len(unnamed)
        cell["named_by_nothing"] += len(unnamed)
        cell["bytes"] += sum(stems[name] for name in unnamed)
        doomed.extend(tracked_name(where / name) for name in unnamed)

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": bool(apply),
        "subtrees": list(POOL_SUBTREES),
        "by_subtree": dict(sorted(by_subtree.items())),
        "reference": reference,
        "pictures_on_disk": sum(cell["pictures"] for cell in by_subtree.values()),
        "carrying_no_row": dict(sorted(unreferenced.items())),
        "named_by_nothing": len(doomed),
        "bytes_named_by_nothing": sum(cell["bytes"] for cell in by_subtree.values()),
        "unmerged": sorted(unmerged, key=lambda held: -held["pictures"]),
        "unmerged_legs": len(unmerged),
        "skipped_unmerged": sum(cell["skipped_unmerged"] for cell in by_subtree.values()),
        "swept_unmerged": sorted(swept, key=lambda held: -held["deleting"]),
        "swept_unmerged_legs": len(swept),
        "swept_unmerged_pictures": sum(held["deleting"] for held in swept),
        "swept_unmerged_bytes": sum(held["bytes"] for held in swept),
    }
    log(
        f"[orphans] {record['pictures_on_disk']:,} pictures; "
        f"{len(unmerged):,} unmerged leg(s) holding {record['skipped_unmerged']:,} were "
        f"skipped, and {len(doomed):,} of the rest are named by no store at all"
    )
    for held in record["swept_unmerged"]:
        log(
            f"[orphans] unmerged and named by the caller: {held['leg']} — deleting "
            f"{held['deleting']:,} of {held['pictures']:,} picture(s), keeping the "
            f"{held['store_named']:,} a store names"
        )
    for held in record["unmerged"]:
        log(
            f"[orphans] unmerged — re-merge or delete: {held['leg']} "
            f"({held['pictures']:,} pictures, {held['store_named']:,} of them named by a "
            f"row this leg never merged)"
        )
    if not apply:
        record["pictures"] = {"would_delete": len(doomed)}
        record["seconds"] = round(time.time() - started, 1)
        return record

    record["pictures"] = delete_pictures(doomed, log=log)
    record["seconds"] = round(time.time() - started, 1)
    return record


def prune(keep: int = RETAIN_PER_PAIR, apply: bool = True, log=print) -> dict:
    """Bring the store back to the settled rule. **Rows and their pictures, together.**

    Top-`keep` per (location, `recipe.mode` **with its `mode_params`**) ranked by the shipped
    [`curation.rank_key`], through [`retention.decide`] rather than a second
    selector — the same body the article teaches the rule with, handed rank values
    instead of a raw `P(>=4)`. Five protections keep a row the rank let go: a seat
    in a live release row, a human rejection, a human label joining it, a row named
    by the rank key's own tracked population file (whose fit stops being
    reproducible if one of them goes), and a seat in a **tentative gallery**,
    whose whole point is that its IDs stay resolvable.

    A dropped row loses **its picture in the same call**. That is the one rule
    now: until 2026-08-29 the pictures were swept on their own ranking at their
    own K and the two were not nested, so a row could be retained with its picture
    already gone. `pictures` says what this freed.

    ## The order is the safety property

    Pictures first, then the record transaction. A crash between them leaves rows
    naming pictures that are not there — which [`picture_census`] reports,
    `solve.pool` refuses, and a second `prune` repairs, because the ranking is a
    deterministic function of the rows. The other order leaves pictures nothing
    names, which is garbage no reader can find and no run can free.

    The three files are then written to `.writing` names and renamed only once all
    three are whole. A sidecar pruned against a ledger that was never written
    would be a store of rows nothing joins to, and the half-written state is the
    one state this must not be able to leave behind.

    ## And it is the only thing that has to write down what it took

    `store.write` is an upsert, so this is where every row that ever leaves the
    ledger leaves it. [`_record_the_ratchet`] therefore runs at the end of the
    transaction, raising [`ratchet`]'s high-water mark to the store's peak and
    recording this prune's drops against it — which is what lets a census assert
    that the store only shrinks for reasons somebody wrote down.

    `apply=False` reads and decides and touches nothing, which is what
    `fractal-wallpapers curate candidate-ledger prune --dry-run` is.
    """
    import time

    from fractal_wallpapers.curation import retention

    started = time.time()
    # Through the path accessors and never off `store_root()`, because those are
    # what a test redirects: `tests/test_candidate_ledger.isolated` moves the two
    # row files and the sidecar by name, and a prune that rebuilt the paths from
    # the root would read past the redirect into the real store and rewrite it.
    # It did exactly that once, on 2026-08-29, and cost 266 pictures.
    files = (store.rows_path(), store.scores_path(), _flatness_path())
    homes = {path.parent for path in files}
    if len(homes) != 1:
        # A REFUSAL and not a repair, because the shape it catches is a test that
        # redirected two of the three and left the third pointing at this
        # machine's real store — which would then be rewritten to hold only the
        # keys of a temporary one. That is not hypothetical: it happened on
        # 2026-08-29, and the sidecar is the one of the three that is reached
        # through another module and so the one a caller forgets.
        raise LedgerError(
            f"the store's three files are in {len(homes)} directories and a prune rewrites "
            f"all three against one set of keys: {[str(path) for path in files]}. Nothing "
            f"was read. If this is a test, redirect `flatness.sidecar_path` too."
        )
    if not files[0].is_file():
        raise LedgerError(f"{files[0]} is not there, so there is nothing to prune.")

    # ---- one pass to decide ------------------------------------------------- #
    meta = _prune_meta(files[0], log=log)
    values, coverage = _prune_ranks(meta, log=log)
    stubs = [
        {
            "key": held["key"],
            "location": {"key": held["place"]},
            "recipe": {"mode": held["mode"], "mode_params": held["settings"]},
            "picture": held["picture"],
        }
        for held in meta
    ]
    verdicts = retention.decide(stubs, values, keep=int(keep))
    protections = _prune_protections(meta, log=log)
    kept_because = dict.fromkeys(RETAINED_REASONS, 0)
    keys: set = set()
    for held in meta:
        key = held["key"]
        ranked = verdicts.get(key) == retention.RANKED
        because = [name for name in RETAINED_REASONS[1:] if key in protections[name]]
        if not ranked and not because:
            continue
        keys.add(key)
        kept_because[RETAINED_RANKED if ranked else because[0]] += 1
    saved = {
        name: sum(1 for key in protections[name] if verdicts.get(key) != retention.RANKED)
        for name in RETAINED_REASONS[1:]
    }
    log(f"[prune] {len(keys):,} of {len(meta):,} rows kept at K={int(keep)}; saved {saved}")

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": bool(apply),
        "keep_per_location_mode": int(keep),
        "store": tracked_name(files[0].parent),
        "rank": coverage,
        "rows_read": len(meta),
        "rows_kept": len(keys),
        "rows_dropped": len(meta) - len(keys),
        "kept_because": kept_because,
        "saved_by_a_protection": saved,
    }
    doomed = [held["picture"] for held in meta if held["key"] not in keys and held["picture"]]
    if not apply:
        record["pictures"] = {"would_delete": len(doomed)}
        record["seconds"] = round(time.time() - started, 1)
        return record

    # ---- the pictures, then the records ------------------------------------- #
    record["pictures"] = delete_pictures(doomed, log=log)
    columns = ("key", "recipe_key", "recipe_key")
    temps = [path.with_suffix(path.suffix + ".writing") for path in files]
    written: dict = {}
    try:
        for name, path, temp, column in zip(
            ("rows", "scores", "flatness"), files, temps, columns, strict=True
        ):
            written[name] = _prune_file(path, temp, keys, column)
        for temp, path in zip(temps, files, strict=True):
            temp.replace(path)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        raise
    for name, held in written.items():
        log(f"[prune] {name}: {held['rows']:,} rows, {held['bytes']:,} bytes")

    record["files"] = written
    record["ratchet"] = _record_the_ratchet(meta, keys, log=log)
    record["seconds"] = round(time.time() - started, 1)
    return record


def _record_the_ratchet(meta: list, keys: set, log=print) -> dict:
    """Advance the high-water mark, then write down what this prune took.

    **After the transaction and never before**, because a mark is a claim about a
    store that exists: a prune that raised the mark and then failed to rename its
    three files would leave the ratchet remembering a size the store never kept,
    and every census after it would read short against a loss nothing could
    account for. The order inside is the other way round — the mark first, then
    the deletion — because the counts `meta` holds are the store at its **peak**,
    after this leg's own rows landed and before the rule took any of them back.

    This is the only recording site because [`_prune_file`] is the only writer
    that drops a row: `store.write` is an upsert and the orphan sweep takes
    pictures alone. See [`ratchet`].
    """
    before = ratchet.counts_of((held["key"], held["picture"]) for held in meta)
    dropped = ratchet.counts_of(
        (held["key"], held["picture"]) for held in meta if held["key"] not in keys
    )
    marked = ratchet.advance(before, why="prune")
    lost = ratchet.record_loss(dropped, why="prune")
    if marked:
        log(f"[prune] the ratchet's mark advanced: {marked['counts']}")
    if lost:
        log(f"[prune] recorded as taken by the rule: {lost['counts']}")
    return {
        "log": tracked_name(ratchet.log_path()),
        "marked": marked["counts"] if marked else None,
        "recorded_as_lost": lost["counts"] if lost else None,
    }


def _flatness_path() -> Path:
    """The flatness sidecar, through its own module's accessor.

    A third name for a path this module already knows how to build would be a
    third thing to redirect, and redirecting two of three is how a test comes to
    rewrite the real store.
    """
    from fractal_wallpapers.curation import flatness

    return flatness.sidecar_path()


def delete_pictures(named, log=print) -> dict:
    """Delete the candidate pictures a prune dropped, and their levelled colormaps.

    `named` is stored names, read through [`paths.rehome`], because a row names
    its picture as the run that made it saw it and the subtree may have been
    archived since. A name with no artifacts component is not a name this project
    wrote and is left alone entirely — which is what keeps a fixture's `a.jpg`,
    and anything beside it, out of reach of this.

    **The levelled colormap goes with the picture**, because it is part of what
    that render cost and the rule is that a picture goes with its row.
    `colorize.render` writes the autolevel operator's overriding map to
    `<stem>.leveled/` beside the JPEG on every acted render, ~76 KiB against the
    picture's ~157 KiB. Unlinking the one and leaving the other is how 206,147 of
    them reached 14.9 GiB — more than the whole candidate pool — and how they
    would do it again. The row re-derives it, so it is regenerable exactly as the
    picture is.

    **That argument is sound HERE and nowhere else.** It holds because the row is
    being dropped in the same transaction, so nothing can name the candidate
    again. It is **not** a licence to sweep the pool's colormaps on their own:
    [`curation.pool_draw`] reads a live candidate's onto every plan unit and
    [`labeling.sheets`] renders through it, and `LEGS.md`'s *`curate pool-draw`*
    records what losing one does — a rebuild serves a different picture under the
    same identity, silently. `curation/README.md`'s *What retention does not
    reach, and the levelled colormaps swept on 2026-08-30* carries the re-sweep.

    The colormap is swept whether or not the JPEG was still there: a row is being
    dropped either way, and a colormap outliving an already-deleted picture is
    precisely the pile.

    Counted rather than raised on: a picture already gone is the ordinary state
    of a store somebody has swept before, and a leg that refused to finish over
    one would leave the records ahead of the disk.
    """
    from fractal_wallpapers.paths import Tiers, rehome

    out = {
        "asked": 0,
        "deleted": 0,
        "bytes": 0,
        "absent": 0,
        "unreadable": 0,
        "colormaps": 0,
        "colormap_bytes": 0,
    }
    # Once above the loop: a prune's doomed list is tens of thousands of names
    # and resolving the tiers per name is 246x the cost of resolving them here.
    tiers = Tiers.current()
    for stored in named:
        out["asked"] += 1
        where = rehome(str(stored), tiers)
        if where is None:
            out["absent"] += 1
            continue
        try:
            size = where.stat().st_size
        except OSError:
            size = None
        if size is None:
            out["absent"] += 1
        else:
            try:
                where.unlink()
            except OSError as failure:
                out["unreadable"] += 1
                log(f"[prune] {where}: {failure!r}")
            else:
                out["deleted"] += 1
                out["bytes"] += size
        # One call site, past every outcome the JPEG can have. A second one
        # inside a branch is how the sweep would come to be skipped for exactly
        # the rows whose picture was already the odd case.
        _delete_colormap(where, out, log)
        if out["deleted"] and out["deleted"] % 25_000 == 0:
            log(f"[prune] {out['deleted']:,} picture(s) deleted, {out['bytes'] / 2**30:.2f} GiB")
    out["gib"] = round(out["bytes"] / 2**30, 3)
    out["colormap_gib"] = round(out["colormap_bytes"] / 2**30, 3)
    log(
        f"[prune] {out['deleted']:,} of {out['asked']:,} picture(s) deleted, {out['gib']} GiB, "
        f"and {out['colormaps']:,} levelled colormap(s), {out['colormap_gib']} GiB"
    )
    return out


def _delete_colormap(picture: Path, out: dict, log) -> None:
    """Remove the `<stem>.leveled/` directory beside one picture, if it has one.

    Spelled the way [`curation.colorize.render`] spells it when it writes the
    thing, so the two cannot drift apart into a writer and a sweeper that
    disagree about the name.
    """

    where = picture.parent / f"{picture.stem}.leveled"
    if not where.is_dir():
        return
    try:
        size = sum(entry.stat().st_size for entry in where.iterdir() if entry.is_file())
        shutil.rmtree(where)
    except OSError as failure:
        out["unreadable"] += 1
        log(f"[prune] {where}: {failure!r}")
        return
    out["colormaps"] += 1
    out["colormap_bytes"] += size


def _prune_meta(path: Path, log=print) -> list[dict]:
    """One streamed pass of the ledger into what the decision needs per row.

    Takes the **file** and not the directory it is in. It took the directory for
    one afternoon and joined `ROWS_NAME` onto a name that was already the file,
    which `_stream_of` answers by yielding nothing — so the prune decided over an
    empty store and wrote three empty files. A silent empty read is what that
    shape of mistake always looks like here, which is why the caller now hands
    every path in and this builds none of its own.
    """
    from fractal_wallpapers.curation import retention

    out: list[dict] = []
    for at, held in enumerate(store._stream_of(path), start=1):
        colour = held.get("colour") or {}
        provenance = held.get("provenance") or {}
        out.append(
            {
                "key": str(held["key"]),
                "place": str((held.get("location") or {}).get("key")),
                "mode": str((held.get("recipe") or {}).get("mode")),
                # The mode's own settings travel too, and they travel APART from
                # `mode` on purpose. `retention._pair_of` groups on the two
                # together, because a mode under settings is its own coloring and
                # its own recipe key; `_Pooled.mode` below stays the bare mode,
                # because the rank key's fitted population is per raw mode and a
                # variant is ranked as what it is a variant OF. Getting these the
                # same way round cost 188 rows and their pictures on 2026-09-02:
                # the stub handed to `decide` carried `mode` alone, so five
                # colorings at a place were still one pair of three seats.
                "settings": dict((held.get("recipe") or {}).get("mode_params") or {}),
                "cells": tuple(colour.get("cells") or ()),
                "rejected": bool(held.get("rejected")),
                "picture": held.get("picture"),
                "render_key": retention.render_key_of(held),
                "seat": (str(provenance.get("run")), str(provenance.get("candidate"))),
                "also_recorded": tuple(
                    (str(named.get("run")), str(named.get("candidate")))
                    for named in (provenance.get("also_recorded") or ())
                ),
            }
        )
        if at % 100_000 == 0:
            log(f"[prune] {at:,} rows read")
    log(f"[prune] {len(out):,} rows read from {tracked_name(path)}")
    return out


class _Pooled:
    """What [`rank_key.features_for`] reads off a candidate, and nothing else."""

    __slots__ = ("cells", "key", "location", "mode", "p_ge3", "score")

    def __init__(self, held: dict, reading: dict):
        self.key = held["key"]
        self.location = held["place"]
        self.mode = held["mode"]
        self.cells = held["cells"]
        self.score = float(reading.get("p_ge4") or 0.0)
        self.p_ge3 = float(reading.get("p_ge3") or 0.0)


def _prune_ranks(meta: list, log=print) -> tuple[dict, dict]:
    """`({key: rank value}, coverage)` through the SHIPPED key, not a copy of it.

    A row the key cannot read — no reading on the live judge, no flatness — has
    no value here, and [`retention.decide`] ranks it last within its pair, which
    is [`curation.solve`]'s own convention for exactly that case.
    """
    from fractal_wallpapers.curation import flatness, intake, rank_key

    readings = rows_module.scores_by_recipe(store.read_scores())
    flat = flatness.by_recipe(flatness.read())
    held = rank_key.load()
    pooled = [_Pooled(row, readings[row["key"]]) for row in meta if row["key"] in readings]
    features, gaps = rank_key.features_for(pooled, locations=intake.read_scores(), readings=flat)
    values = {name: held.score(row) for name, row in features.items()}
    log(f"[prune] {len(values):,} of {len(meta):,} rows carry a rank value; gaps {gaps}")
    return values, {
        "artifact": tracked_name(rank_key.artifact_path()),
        "fitted_at": held.document.get("fitted_at"),
        "columns": list(held.columns),
        "rows": len(meta),
        "with_a_live_score": len(pooled),
        "ranked": len(values),
        "unranked": len(meta) - len(values),
        **gaps,
    }


def _prune_protections(meta: list, log=print) -> dict:
    """`{reason: {keys}}` for the five things kept whatever the rank says."""
    from fractal_wallpapers.curation import rank_key, retention, served_locations, tentative

    index = served_locations.build()
    live: set = set()
    for held in index.rows:
        live.add((str(held.get("run")), str(held.get("candidate"))))
        source = held.get("source") or {}
        if source.get("run") is not None:
            live.add((str(source.get("run")), str(source.get("candidate"))))
    marked = retention.labeled_renders()
    recorded = tentative.protected_keys()
    fitted = {
        str(json.loads(line)["recipe_key"])
        for line in rank_key.population_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    out = {
        RETAINED_SEATED: {
            held["key"]
            for held in meta
            if held["seat"] in live or any(named in live for named in held["also_recorded"])
        },
        RETAINED_REJECTED: {held["key"] for held in meta if held["rejected"]},
        RETAINED_LABELED: {held["key"] for held in meta if held["render_key"] in marked},
        RETAINED_FITTED: {held["key"] for held in meta if held["key"] in fitted},
        RETAINED_TENTATIVE: {held["key"] for held in meta if held["key"] in recorded},
    }
    named = ", ".join(f"{name} {len(found):,}" for name, found in out.items())
    log(
        f"[prune] protections: {named}; the population file names {len(fitted):,} recipe(s) "
        f"and {len(tentative.stamps())} recorded gallery/ies name {len(recorded):,}"
    )
    return out


def _prune_file(source: Path, into: Path, keys: set, column: str) -> dict:
    """Stream one recipe-keyed file into a `.writing` name, its kept rows only.

    One body for the ledger and both sidecars: the only thing that differs is
    which column carries the recipe key, and two copies of a filter is how a
    sidecar comes to be pruned against a rule the rows were not.
    """
    rows = 0
    dropped = 0
    with into.open("w", encoding="utf-8", newline="\n") as handle:
        for held in store._stream_of(source):
            if str(held.get(column)) not in keys:
                dropped += 1
                continue
            handle.write(json.dumps(held, ensure_ascii=False) + "\n")
            rows += 1
    return {"rows": rows, "dropped": dropped, "bytes": into.stat().st_size}


def remove(keys, why: str, apply: bool = True, log=print) -> dict:
    """Take the **named** rows out of the store, their pictures with them.

    The second row-dropping transaction, and for a long time there was only
    [`prune`]'s. It is here because a pass that *replaces* a row has to be able to
    take the row it replaced: [`curation.rotation`] adopts a rotation of a recipe
    and the recipe it rotated is then a picture the store is keeping twice, and
    there was no verb for that. Adding one is a decision rather than a repair —
    the argument for a single deletion site was that a store nothing else deletes
    from is a store whose losses the [`ratchet`] can account for by reading one
    transaction — so this keeps that property rather than spending it: **it
    records its loss exactly as a prune does**, and the ratchet's reading is
    unchanged by which of the two wrote the row.

    What it is **not** is a rule. `prune` decides; this is told. The caller names
    the keys and owns every protection it meant to honour, which is the one thing
    that makes a general delete verb safe to have at all — see
    [`curation.rotation.protections`] for the set the one caller honours, which is
    the prune's own five and not a shorter list.

    The order is [`prune`]'s and it is the safety property: pictures first, then
    the record transaction, then the mark. A crash between the first two leaves
    rows naming pictures that are not there — which [`picture_census`] reports and
    a `re-render` puts back — and the other order leaves pictures nothing names,
    which is garbage no reader can find.

    `apply=False` decides and touches nothing.
    """
    started = time.time()
    named = {str(key) for key in keys}
    if not named:
        raise LedgerError("remove() was named no key, so there is nothing to take")
    files = (store.rows_path(), store.scores_path(), _flatness_path())
    homes = {path.parent for path in files}
    if len(homes) != 1:
        # [`prune`]'s refusal, for [`prune`]'s reason: a test that redirected two
        # of the three would have this rewrite the third — this machine's real
        # store — to hold only the keys of a temporary one.
        raise LedgerError(
            f"the store's three files are in {len(homes)} directories and a removal rewrites "
            f"all three against one set of keys: {[str(path) for path in files]}. Nothing "
            f"was read. If this is a test, redirect `flatness.sidecar_path` too."
        )
    if not files[0].is_file():
        raise LedgerError(f"{files[0]} is not there, so there is nothing to remove from.")

    meta = [
        (str(row["key"]), row.get("picture"))
        for row in store.stream(files[0])
        if str(row["key"]) in named
    ]
    found = {key for key, _picture in meta}
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": bool(apply),
        "why": str(why),
        "named": len(named),
        "in_the_store": len(meta),
        "not_in_the_store": len(named - found),
        "store": tracked_name(files[0].parent),
    }
    log(f"[remove] {len(meta):,} of {len(named):,} named row(s) are in the store")
    doomed = [picture for _key, picture in meta if picture]
    if not apply or not meta:
        record["pictures"] = {"would_delete": len(doomed)}
        record["seconds"] = round(time.time() - started, 1)
        return record

    record["pictures"] = delete_pictures(doomed, log=log)
    columns = ("key", "recipe_key", "recipe_key")
    temps = [path.with_suffix(path.suffix + ".writing") for path in files]
    written: dict = {}
    try:
        for name, path, temp, column in zip(
            ("rows", "scores", "flatness"), files, temps, columns, strict=True
        ):
            written[name] = _remove_from_file(path, temp, found, column)
        for temp, path in zip(temps, files, strict=True):
            temp.replace(path)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        raise
    for name, held in written.items():
        log(f"[remove] {name}: {held['rows']:,} rows, {held['dropped']:,} dropped")
    record["files"] = written
    # The ratchet, for [`prune._record_the_ratchet`]'s reason and with no mark:
    # this transaction only ever shrinks the store, and a mark is a claim about a
    # size the store reached.
    lost = ratchet.record_loss(ratchet.counts_of(meta), why=str(why))
    record["ratchet"] = {
        "log": tracked_name(ratchet.log_path()),
        "recorded_as_lost": lost["counts"] if lost else None,
    }
    record["seconds"] = round(time.time() - started, 1)
    return record


def _remove_from_file(source: Path, into: Path, keys: set, column: str) -> dict:
    """Stream one recipe-keyed file into a `.writing` name, minus the named rows.

    [`_prune_file`]'s inverse — that one is told what to keep and this one what to
    drop — and a separate body rather than a flag, because the two differ in the
    direction of one comparison and a caller that got the flag the wrong way round
    would delete the complement of what it meant to.
    """
    rows = 0
    dropped = 0
    with into.open("w", encoding="utf-8", newline="\n") as handle:
        for held in store._stream_of(source):
            if str(held.get(column)) in keys:
                dropped += 1
                continue
            handle.write(json.dumps(held, ensure_ascii=False) + "\n")
            rows += 1
    return {"rows": rows, "dropped": dropped, "bytes": into.stat().st_size}
