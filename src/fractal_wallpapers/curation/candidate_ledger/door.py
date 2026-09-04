"""THE door: every leg's rows, upserted, recorded, and pruned back to the rule.

One function, and it is here on its own because of what it reaches. A merge
sweeps the flatness sidecar, prices the repeat draws, runs [`sweep.prune`] and
records four files — so it imports the retention rule, the colormaps and two
sidecars, and a store that lived beside it would carry all of that on its back.
[`store`] is the bottom of this package precisely because this is not in it.
"""

from __future__ import annotations

from fractal_wallpapers.curation import durability
from fractal_wallpapers.curation.candidate_ledger import store, sweep
from fractal_wallpapers.paths import tracked_name


def merge(rows, scores, log=print) -> dict:
    """Upsert a leg's rows, record them, prune the store back to the rule.

    THE door. Every leg that adds to the ledger — a hunt, a mine, a depth run,
    the backfill — comes through here, and there is one body rather than four
    copies of an upsert followed by a save each of them has to remember. It is
    also the only door the retention rule needs to stand at.

    **The tracking is the point.** The manifests are the only thing about this
    store the history keeps, and they went stale for an era: three merge legs and
    the backfill all wrote the rows and none of them recorded what they wrote, so
    the manifest said 16,006 rows against 128,368 live and `curate
    candidate-ledger check` could only ever answer `grown`. A writer that has to
    remember to record is a writer that will stop, so the record is not something
    a caller does afterwards — it is the second half of the write.

    **And the flatness sidecar is filled here, for the same reason.** It is keyed
    on the recipe and nothing else fills it, so a leg that merged and stopped left
    every row it wrote **unranked** to [`curation.rank_key`] — which is what
    `curate seat` orders on by default. Unranked rows sort last and are never
    refused, so they sat in the pool, cleared their bars, counted in every
    denominator, and could not win a seat while a ranked row was left:
    `mine1h` merged 8,192 rows and seated none of them, silently. The sweep is
    incremental and reads only pictures the sidecar has never seen — 33 s for
    those 8,192 — so a merge with nothing new to read pays one file read.

    **And [`prune`] runs here, which is the half that makes the store bounded.**
    A merge is the only thing that grows this file, so it is the only place the
    rule has to act; anywhere else and a rule nothing runs is a rule the store
    stops obeying between the times somebody remembers it. Rows per (location,
    mode) cannot exceed [`RETAIN_PER_PAIR`] after this returns, and the pictures
    of the rows it drops are gone with them. Deciding is **18.4 s** over the
    122,516 rows standing on 2026-08-29, and rewriting the three files is about as
    much again — paid at the end of a leg measured in minutes or hours, which is
    the same trade the flatness sweep above it makes.

    The **copy** goes with the manifest, because that is what the manifest is a
    claim about: [`durability.save`] writes both or neither, and a manifest naming
    a count no copy holds would make [`durability.restore`] believe a stale file.
    It is written **after** the prune and not before: a manifest recording the
    pre-prune count would make [`durability.check`] read `short` on a store that
    is exactly what the rule says it should be.

    **All four files are recorded, not two.** The flatness sidecar is written by
    the sweep above and rewritten by the prune below, and for an era it was saved
    only when somebody ran `curate flatness save` by hand — so the one file whose
    absence silently unranks a merge's whole output was the one file the door did
    not record. The reduced-signature sidecar joined it for the weaker but real
    version of the same reason: nothing here fills it, but a restore without it
    re-derives 68.6 MB of readings the mirror could have copied. Note what this
    does *not* buy: `curate candidate-ledger check` still reads the rows and the
    scores alone, so a short or missing sidecar is not what makes that command
    exit 1. Extending it is a decision about what a build failure is, and it has
    not been taken here.
    """
    from fractal_wallpapers.curation import colorize, flatness, retention, signatures

    # Before the upsert, because it is a reading of what the store held BEFORE
    # this leg's own rows joined it — see [`retention.repeat_draws`].
    standing = retention.drawn_before(store.stream())
    repeated = retention.repeat_draws(rows, standing, pool=len(colorize.pool(0)))
    log(
        f"[ledger] {repeated['at_locations_with_deleted_rows']:,} of {len(rows):,} row(s) "
        f"land at a location holding deleted recipes; at most {repeated['bound']:,} and "
        f"about {repeated['expected']} of them are renders this project already paid for"
    )

    rows_file, total, new = store.write(rows)
    scores_file, score_total, score_new = store.write_scores(scores)
    swept = flatness.sweep(flatness.of_rows(rows), log=log)
    pruned = sweep.prune(log=log)
    saved = {
        "rows": durability.save(store.durable_rows(), log=log),
        "scores": durability.save(store.durable_scores(), log=log),
    }
    # The flatness sidecar is the third file of this store and the prune above
    # rewrites it, so it is recorded here with the other two rather than left to
    # `curate flatness save` by hand — which is the only reason its manifest was
    # ever current. Conditional where they are not, and the reason is not the
    # sweep: `flatness.sweep` writes no file when it read nothing, but `prune`
    # rewrites all three and runs between them, so the sidecar is here by now and
    # a merge that swept nothing records it empty. The test is what keeps
    # [`durability.save`]'s refusal — it raises on a file that is not there —
    # from turning a checkout that has never swept into a failed merge.
    if flatness.sidecar_path().is_file():
        saved["flatness"] = durability.save(flatness.durable(), log=log)
    # The reduced-signature sidecar is the fourth, and conditional for a stronger
    # version of the flatness sidecar's reason: nothing in a merge fills it, so on
    # a checkout that has never run `curate signatures sweep` there is no file at
    # all. Where there is one it is mirrored here rather than left to a restore to
    # re-derive over the three-worker pool, which is minutes for bytes a copy
    # already had.
    if signatures.sidecar_path().is_file():
        saved["signatures"] = durability.save(signatures.durable(), log=log)
    return {
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "ledger": {"rows": total, "new": new},
        "scores": {"rows": score_total, "new": score_new},
        "flatness": {
            "column": swept["column"],
            "swept": swept["swept"],
            "read": swept["read"],
            "unreadable": swept["unreadable"],
            "seconds": swept["seconds"],
        },
        "repeat_draws": repeated,
        "pruned": pruned,
        "recorded": {
            "rows": saved["rows"]["rows"],
            "scores": saved["scores"]["rows"],
            "flatness": saved["flatness"]["rows"] if "flatness" in saved else None,
            "signatures": saved["signatures"]["rows"] if "signatures" in saved else None,
            "manifests": [
                tracked_name(store.durable_rows().manifest),
                tracked_name(store.durable_scores().manifest),
                *([tracked_name(flatness.durable().manifest)] if "flatness" in saved else []),
                *([tracked_name(signatures.durable().manifest)] if "signatures" in saved else []),
            ],
        },
    }
